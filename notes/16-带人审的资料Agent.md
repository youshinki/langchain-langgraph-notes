---
series: langchain-langgraph-notes
篇号: 16
标题: 带人审的资料 Agent
副标题: HumanInTheLoopMiddleware、四种决定与恢复
版本锚定: langchain 1.5.x / langgraph 1.2.x / langgraph-cli 0.4.x / Python 3.11+
状态: 初稿
配图: 3 张（1:1 深色科技风）
---

## 正文

# 第16篇：带人审的资料 Agent｜LangGraph系列

欢迎来到《把 Agent 画成图：18 篇吃透 LangChain 与 LangGraph》，这是第 16 篇。从 LangChain 1.x 的 `create_agent` 讲到 LangGraph 运行时，再到工程化落地。

上一篇把图变成了服务。这一篇给它加一个真场景：资料 Agent——查内部文档、带着引用写出答复、再往外发。外发这一步不能全自动，必须有个人按一下。难点不在"停一下"，而在停下来之后还能改参数、能拒绝、能留痕。

## 一、场景：三步里只有一步该拦

先把这个 Agent 的活拆清楚：

1. **找资料**：`search_docs` 检索知识库，返回带来源的片段；
2. **成稿**：模型基于片段写答复，每句后面带引用编号；
3. **外发**：`send_reply` 把答复发给用户，或写进工单。

前两步错了顶多白跑，第三步错了就是对外事故。所以人审的闸门应该卡在第三步之前，而不是在每个节点上都弹窗。审得太碎，没人愿意用；一处不审，出事就是大事。

判断标准很简单：**这一步有没有不可逆的外部副作用**。有，就拦；没有，就让模型自己跑。

还有一层现实约束：资料库是有时效的。政策改了、价格调了，模型检索到的旧片段可能还停在检查点里。所以审批界面必须把"依据哪几段、什么时候抓的"一起摆出来，否则审的是结论，不是事实。

## 二、人审不是加个确认弹窗

很多实现是在前端加个"确认发送"按钮，后端照跑不误。这不算人审，因为：

- 拦不住：模型已经把消息发出去了，按钮只是事后通知；
- 改不了：审的人只能说行或不行，不能说"把金额改成 39 元再发"；
- 留不下：谁批的、批的是哪一版参数，事后查不到。

LangChain 1.5 里这套东西叫 `HumanInTheLoopMiddleware`，挂在 agent 的 middleware 链上，按工具名配策略。它会在工具真正执行前抛一个 `interrupt`，把图和状态一起冻在检查点里，等人回话再继续。

前提是**必须配 checkpointer**。没有持久化，图停了就找不回来——这条没有例外。

## 三、把审批装进 middleware

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="openai:gpt-5",
    tools=[search_docs, send_reply, update_ticket],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "send_reply": True,                                    # 四种决定都允许
                "update_ticket": {"allowed_decisions": ["approve", "reject"]},
                "search_docs": False,                                  # 只读，不拦
            },
            description_prefix="外发前请复核",
            interrupt_mode="per_call",
        ),
    ],
    checkpointer=InMemorySaver(),   # 生产换 AsyncPostgresSaver
)
```

`interrupt_on` 三个值：`True` 全开、`False` 放行、或一个配置对象。配置对象里 `allowed_decisions` 限定可用的决定类型，`when` 收一个 `ToolCallRequest` 做条件判断，`description` 可以写死也可以给函数。

`when` 很实用：只在"发给外部客户"时拦，内部备注直接过。

```python
def is_external(request) -> bool:
    return not request.tool_call["args"].get("to", "").endswith("@internal.com")

interrupt_on={"send_reply": {"allowed_decisions": ["approve", "edit", "reject"],
                             "when": is_external}}
```

有个坑要知道：**恢复时 `when` 会再跑一次，必须给出同样的结果**。同一个调用前后判断不一致，中间件会报 `ValueError`，或者干脆放行、把审核意见丢掉。

## 四、四种决定，别用错

| 决定 | 行为 | 模型收到什么 |
|---|---|---|
| `approve` | 按原参数执行 | 工具真实结果 |
| `edit` | 改参数后执行 | 改后的工具结果，前面带一句"人改过这次调用" |
| `reject` | 跳过不执行 | 一条 error 状态的工具消息，附拒绝理由 |
| `respond` | 不执行，直接把人写的话当结果 | 成功状态的工具消息 |

最容易错的是 `reject` 和 `respond`：拒绝**必须**用 `reject`，因为它是 error 状态，模型知道这一步失败了；`respond` 会被当成成功结果，用它去拒绝一个外发动作，模型会以为已经发出去了。

`edit` 要克制。参数改得太多，模型会重新评估整个计划，可能再调一次工具，或者绕去别的路径。改个收件人、改个金额没问题，别整段重写。

## 五、一次审一批，还是一次审一个

`interrupt_mode` 两档：

- `batched`（默认）：一个模型轮次里所有要审的调用合成一个中断，回答是一串按顺序排的决定；
- `per_call`：每个调用单独一个中断，每个中断有自己的 ID 和 `response_schema`，按 ID 回答。

新写的 Agent 建议直接上 `per_call`（需要 `langchain>=1.4.6`）。批量的顺序靠位置对齐，一旦前端少传一个，后面的决定全错位；按 ID 就不会串。

中断的值长这样，`type` 固定是 `tool_approval`，前端靠它区分"这是审批"还是别的中断：

```python
{
    "type": "tool_approval",
    "tool_call_id": "call_send",
    "name": "send_reply",
    "args": {"to": "user@example.com", "body": "退款 39 元已原路退回……"},
    "description": "外发前请复核\n\nTool: send_reply\nArgs: {...}",
}
```

## 六、恢复：按顺序，还是按 ID

本地跑的时候，拿 `version="v2"` 的返回值，从 `result.interrupts` 里取：

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "把这个工单的退款结论发给客户"}]},
    config={"configurable": {"thread_id": "t-1024"}},
    version="v2",
)
for it in result.interrupts:
    print(it.id, it.value["name"], it.value["args"])
```

回答时，`batched` 给列表，`per_call` 给字典：

```python
from langgraph.types import Command

# per_call：按中断 ID 一个决定
agent.invoke(Command(resume={it.id: {"type": "edit",
              "edited_action": {"name": "send_reply",
                                "args": {"to": "user@example.com", "body": "退款 39 元已原路退回。"}}}}),
             config=config, version="v2")

# batched：按顺序给一串
agent.invoke(Command(resume=[{"type": "approve"}, {"type": "reject", "message": "先别写工单"}]),
             config=config, version="v2")
```

两个细节值得记：**没回答的中断会保持 pending**，不会超时消失；**回答不合法会抛 `ValidationError`，且什么都不落盘**，可以改对了再答一次同一个 ID。但一批里混进一个坏答案时，其它工具的调用可能已经执行，重复提交就会跑两遍——要么先按 `response_schema` 校验，要么一个一个答。

## 七、服务端的恢复动作

上了 Agent Server，恢复不是调 `invoke`，而是往同一条 thread 再发一个 run，把 `command` 带进去：

```python
from langgraph_sdk import get_client

client = get_client(url="http://127.0.0.1:2024")
await client.runs.wait(
    thread_id,
    "agent",
    command={"resume": {interrupt_id: {"type": "approve"}}},
)
```

`runs.wait` 会等到这一轮跑完再返回，要流式就换 `runs.stream`。中断本身挂在 thread 的状态里，`threads.get_state` 能看到 pending 的任务和它们的 `interrupts`——审核界面就靠这个列表渲染"待办"。

这里和第 15 篇的规则接上了：一条 thread 同时只跑一个 run。所以审核期间这条 thread 是占着的，要么等审完，要么显式取消；别指望一边等人一边并发跑下一轮。

## 八、让审批这件事可信

四个工程细节，缺一个就出问题：

1. **检查点要持久**：`InMemorySaver` 只适合本地，重启即丢，生产用 `AsyncPostgresSaver` 或 `MongoDBSaver`；
2. **审计字段进 metadata**：`reviewer_id`、`review_action`、`reviewed_at` 写进 run 的 metadata，配第 14 篇的 trace，事后能还原"谁在哪一步改了什么"；
3. **中间件顺序**：`HumanInTheLoopMiddleware` 要放在重试、错误处理中间件之前，否则重试会把审核再问一遍；
4. **半截调用要能收场**：`interrupt` 可能停在工具调用已发起、结果未回的时刻，恢复逻辑要允许"重跑这个工具"，工具本身得幂等。

再加两条产品侧的：审核界面别只给一句"是否通过"，要把 `args` 摊开、把引用来源列出来——审的人看不到依据，按通过只是走个形式；审核待办也要有队列和归属，堆在一个共享列表里，最后就是没人认领、集体拖延。

## 九、一句话收尾

一句话记：**人审的价值不在"停"，在"停下来的那一刻，状态是可查、可改、可拒绝的"。**

`interrupt` 负责停，checkpointer 负责存，`Command(resume=...)` 负责续，`response_schema` 负责让答案不跑偏。四件凑齐，才叫能上线的人审。

这是《把 Agent 画成图：18 篇吃透 LangChain 与 LangGraph》的第 16 篇。下一篇把单个 Agent 扩成研究小组，讲多 Agent 的编排与交接。
