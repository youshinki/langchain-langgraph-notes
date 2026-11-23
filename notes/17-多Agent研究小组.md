---
series: langchain-langgraph-notes
篇号: 17
标题: 多 Agent 研究小组
副标题: subagents、handoffs 与上下文隔离
版本锚定: langchain 1.5.x / langgraph 1.2.x / langgraph-cli 0.4.x / Python 3.11+
状态: 初稿
配图: 3 张（1:1 深色科技风）
---

## 正文

# 第17篇：多 Agent 研究小组｜LangGraph系列

欢迎来到《把 Agent 画成图：18 篇吃透 LangChain 与 LangGraph》，这是第 17 篇。从 LangChain 1.x 的 `create_agent` 讲到 LangGraph 运行时，再到工程化落地。

上一篇的 Agent 只干一件事：查资料、写答复、等人批。如果任务变成"调研三家竞品的定价策略，写成一份对比，再自查一遍引用"，一个 Agent 就会开始乱：工具太多选不准、上下文越滚越脏、一处出错全盘重来。这一篇讲怎么拆成一个小组。

## 一、什么时候该拆

先别急着上多 Agent。三个信号出现了才值得拆：

1. **工具太多**：三十个工具塞给一个模型，选错的概率随数量上升，提示词也压不住；
2. **上下文太脏**：检索回来的几十段原文、几轮试错，全堆在同一个窗口里，后面的判断被前面的噪声带偏；
3. **职责冲突**：写手要发散，校对要挑刺，同一个人格干不了两件相反的事。

反过来，如果只是"工具有五个、任务三步"，拆成多 Agent 只会多付延迟和 token，还多出一堆调试成本。**拆分的理由是上下文隔离和职责专一，不是显得架构高级。**

## 二、三种结构，先认清楚

官方现在推荐两条主路，加上一条老路：

- **subagents（子 Agent 即工具）**：一个主管 Agent，把每个专员包成工具。所有路由都回主管，专员之间不直接对话，也不直接面对用户。这是当前主推的写法。
- **handoffs（交接）**：多个 Agent 各自是图里的节点，靠工具调用把控制权交出去，`Command(goto="writer")` 一类。适合"接待—转专员—再转回来"的会话流。
- **hierarchical（分层）**：专员多到主管管不过来时，先分组，再给组配主管，顶层主管只管几个组。

一个现实提醒：`langgraph-supervisor` 这个包已经不再积极维护，官方迁移指南让你直接用"把子 Agent 包成工具"的写法，别再从旧包里找 `create_supervisor`。

handoff 的交接长这样，注意消息要自己配好：

```python
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool
def transfer_to_writer(runtime: ToolRuntime) -> Command:
    return Command(
        goto="writer",                    # 交接到哪个节点
        update={"messages": [ToolMessage(content="已交接，材料在上一条",
                                         tool_call_id=runtime.tool_call_id)]},
    )
```

要让父图的节点接手，再补一个 `graph=Command.PARENT`。

## 三、小组怎么搭：主管 + 三个专员

以一个研究小组为例：检索员负责找资料，写手负责成稿，校对负责挑引用错误。

```python
from langchain.agents import create_agent

research_agent = create_agent(
    model="openai:gpt-5",
    tools=[search_docs, fetch_page],
    system_prompt="你是检索员。只返回与问题直接相关的片段，每条带来源链接和抓取时间。",
)
writer_agent = create_agent(
    model="openai:gpt-5",
    tools=[outline_tool],
    system_prompt="你是写手。基于给定材料成稿，每句结论后标注来源编号，不许自行补充事实。",
)
reviewer_agent = create_agent(
    model="openai:gpt-5",
    tools=[check_citation],
    system_prompt="你是校对。逐条核对引用是否支撑结论，输出问题清单，不要改写正文。",
)
```

三个专员都**没有**配 checkpointer、也没有互相调用的工具——它们是被调用的，不是自己跑的。

## 四、一人一个工具，还是一个 task 派活

包成工具有两种写法。人少（十个以内）就一人一个工具，描述写清楚，主管按描述选：

```python
from langchain.tools import tool

@tool("research", description="调研一个主题并返回带来源的要点")
def call_research(query: str) -> str:
    result = research_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return result["messages"][-1].content

@tool("write", description="把材料写成结构化成稿，带引用编号")
def call_write(brief: str) -> str:
    result = writer_agent.invoke({"messages": [{"role": "user", "content": brief]}]  )
    return result["messages"][-1].content

main_agent = create_agent(
    model="openai:gpt-5",
    tools=[call_research, call_write],
    system_prompt="你是研究组长。先派检索，再派写作，最后派校对；每次只派一个。",
)
```

专员多、或者由不同团队各自维护时，改成一个 `task(agent_name, description)` 的派发工具，主管按名字调用。好处是加新专员不用改主管的提示词，坏处是每个专员的个性只能靠注册表和描述表达。

这里的命名和描述不是装饰，**主管就是靠它们选人的**。`research` 这种名字太泛，改成 `research_pricing` 之类的动作名，选错的概率会明显下降。

## 五、上下文怎么给：隔离还是继承

默认是**隔离**：专员只拿到你传进去的那段任务描述，前面的对话历史一概看不到。这就是上下文隔离的价值——它在干净窗口里干活，不会把主对话越滚越脏。

但有些活需要"接着刚才的"干，比如继续改上一版稿子。这时从工具的运行时状态里把历史取出来传进去：

```python
from langchain.tools import tool, ToolRuntime
from langchain.agents import AgentState

@tool("revise", description="在上一版基础上修改")
def call_revise(query: str, runtime: ToolRuntime[None, AgentState]):
    history = runtime.state["messages"][-6:]        # 只给最近六条，别全塞
    result = writer_agent.invoke({"messages": [*history,
                                  {"role": "user", "content": query}]})
    return result["messages"][-1].content
```

取多少历史是自己定的工程决策：全给，等于放弃隔离；给太少，专员又得重新猜。实践中按"够它接着干"的最小切片给，通常三到六条。

## 六、结果怎么收：只回摘要会丢东西

最简单的收法是返回最后一条消息的文本。问题是：专员调了哪些工具、查了哪些来源、哪几条被它判为不相关，主管一概看不到，于是下一轮又得重复查一遍。

需要结构化回报时，用 `Command` 把字段和消息一起带回父图：

```python
from typing import Annotated
from langchain.tools import InjectedToolCallId
from langchain.messages import ToolMessage
from langgraph.types import Command

@tool("research", description="调研并回传来源清单")
def call_research(query: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
    result = research_agent.invoke({"messages": [{"role": "user", "content": query}]})
    return Command(update={
        "sources": result.get("sources", []),
        "messages": [ToolMessage(content=result["messages"][-1].content,
                                 tool_call_id=tool_call_id)],
    })
```

注意 `ToolMessage` 必须带上 `tool_call_id`，否则父图的消息配对会断——这是 handoff 和工具返回里最常见的报错来源。

## 七、并行：一个轮次派三个

主管在同一轮里发出多个工具调用，运行时会把它们并行执行。调研三家竞品，就一轮派三个检索，比串行快三倍。前提是三个子任务**互不依赖**，且各自的输出不会写同一个 key——并行写同一个字段会冲突，这坑第 06 篇讲过，用 reducer 或分开的 key。

再大一点的扇出（数量不定、要按列表分发），用 `Send` 走 map-reduce：一个 `Send` 一个专员实例，最后在 reducer 里合并。

```python
from langgraph.types import Send

def fan_out(state):
    return [Send("research_one", {"topic": t}) for t in state["topics"]]
```

三个竞品也好，三十个也好，条件边返回的是一串 `Send`，运行时并行跑，谁先回谁先落。

## 八、四个必踩的坑

1. **子 Agent 不可发现**：它是在工具函数里 `invoke` 的，LangGraph 静态扫不到，`get_state(subgraphs=True)` 不会返回它的状态。想在中断时看它的中间态，得把它放进自定义图的节点里跑。
2. **检查点是继承来的**：默认每次调用都是干净状态，中断能正常用、并行也安全；要让它跨调用记住自己的会话，编译时加 `checkpointer=True`，代价是少了隔离。
3. **handoff 的消息要自己配**：两个独立子图之间交接，`Command(goto=..., update={...})` 里传什么消息得显式决定，传错就是畸形历史或上下文爆炸；跨层交回父图用 `Command(graph=Command.PARENT)`。
4. **错误会放大**：一个专员跑歪，主管可能基于错结果继续派活。所以每个专员的输出都要带可核验的东西——来源、行号、耗时，别只给一段自信的文字。

## 九、一句话收尾

一句话记：**多 Agent 不是把活儿分给更多人，是把上下文分成几个干净的房间，每个房间只放一件事。**

真要拆，先问三个问题：这个专员需要看到多少历史？它回什么才算有用的结果？它跑歪了谁能发现？三个都答得上来，再动手加第二个 Agent。

这是《把 Agent 画成图：18 篇吃透 LangChain 与 LangGraph》的第 17 篇。下一篇收尾：四种编排方式到底怎么选，把这 17 篇的选择收成一张表。
