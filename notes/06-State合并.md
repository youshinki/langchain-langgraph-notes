---
series: langchain-langgraph-notes
篇号: 06
标题: State 怎么合并
副标题: reducer、并行写冲突与 Overwrite
版本锚定: langchain 1.5.0 / langgraph 1.2.x / Python 3.11+
状态: 初稿
配图: 3 张（1:1 深色科技风）
---

## 正文

# 第06篇：State 怎么合并｜LangGraph系列

欢迎来到《把 Agent 画成图：18 篇吃透 LangChain 与 LangGraph》，这是第 06 篇。从 LangChain 1.x 的 `create_agent` 讲到 LangGraph 运行时，再到工程化落地。

第 05 篇收掉了 LangChain 侧，从这一篇开始进 LangGraph 运行时。第一件事是最基础也最容易踩坑的：多个节点同时改 state，值到底怎么合并。

## 一、State 不是一个字典

`StateGraph` 里的 state 看着像 `TypedDict`，编译之后其实是一组 channel。每个 key 对应一个 channel，channel 记两样东西：当前值，以及"新值怎么并进来"的规则。

节点返回的是 patch，不是完整状态。你写 `return {"docs": [...]}`，框架拿这个 patch 去问 `docs` 这个 channel：这一笔怎么合。规则就是 reducer。

没配 reducer 的 channel 用默认规则：**last write wins，直接覆盖**。所以 `question` 没出现在返回值里，它就保持原样——不是"被清空"，是"没被碰过"。

```python
from typing_extensions import TypedDict

class State(TypedDict):
    question: str
    docs: list[str]
```

这两个 key 都是默认 channel。串行图里这样最省事：一次只有一个写者，覆盖就是最自然的语义。

内部实现上，channel 其实分三类：`LastValue` 只留最后一个值；`Topic` 是队列，适合事件流；`BinaryOperatorAggregate` 才是我们常说的 reducer，每来一笔就做一次二元合并。你写不写 `Annotated`，选的就是这几种 channel。

## 二、新手最容易犯的错：把整个 state 返回

`return state` 看着安全，实际很糟。它把每个 key 都当成"要更新"，于是并行分支里那些没动过的字段也被重新写了一遍，后面的分支写什么都会被盖掉。

正确姿势是只返回你改动的字段。少写一个 key，那个 key 就不参与这一轮的合并，也就不会跟别人打架。

覆盖在串行场景里很安全，但并行时它没有"顺序"可言。两个分支谁先写、谁后写，取决于框架内部的 task path 排序，不是你的代码顺序。这也解释了一个常见困惑：本地跑十次都对，上线偶尔丢数据——那不是玄学，是覆盖遇上并发。

## 三、add_messages 不是普通追加

消息列表是唯一一个"必须配 reducer"的字段：`Annotated[list[AnyMessage], add_messages]`。

它做三件事：新消息追加；同 `id` 的消息覆盖原消息；`RemoveMessage` 删除指定消息。换成 `operator.add` 就只剩追加，人工编辑历史消息时改不动，删除也做不到。

```python
from typing import Annotated
from langchain.messages import AnyMessage
from langgraph.graph.message import add_messages

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
```

第 02 篇讲过"同 id 覆盖"的语义，落到实现上，就是这个 reducer 在做事。`MessagesState` 只是把它预置好，再让你加字段。

删除要显式构造一条 `RemoveMessage`，带上目标消息的 `id`，返回给 `messages`。它不是"从列表里 pop"，而是发一条指令让 reducer 处理。这个设计的好处是删除本身也进历史，回溯时看得见。

## 四、并行分支写同一个 key 会报错

两条边从同一个节点扇出，两个分支属于同一个 super-step。它们读到的都是同一份旧状态，写回时如果这个 key 没有 reducer，框架不知道听谁的，直接抛 `InvalidUpdateError`，提示大致是"这个 key 每一步只能收到一个值"。

这是保护而不是 bug。静默丢掉一个分支的结果，比报错难查得多。

解法有两条：给这个 key 配 reducer，让它能合并；或者让两个分支写不同字段，从设计上避免冲突。后者通常更好，因为合并语义是你要能解释清楚的东西。

排查这类错误有个笨办法但很有效：把两个分支的返回值打印出来，看它们有没有交集。交集只有一个 key，就把它拆成两个；交集成片，说明你的状态划分本身有问题，应该拆图而不是加 reducer。

## 五、reducer 是二元函数

签名是固定的：`reducer(left=当前值, right=本次更新)`，返回值就是合并后的新值。

```python
import operator

class State(TypedDict):
    hits: Annotated[list[str], operator.add]
    count: Annotated[int, operator.add]
```

`operator.add` 对列表是拼接，对整数是相加。字典没有现成的 reducer，得自己写：

```python
def merge_dict(left: dict, right: dict) -> dict:
    """浅合并，右边的键赢。"""
    return {**left, **right}

class State(TypedDict):
    config: Annotated[dict, merge_dict]
```

浅合并只顶第一层，嵌套字典会被整体替换。要深合并，要么递归写，要么交给专门的合并库，别指望一行 `{**a, **b}` 解决。

同一个 reducer 也常被用来做"取最大""去重"这类聚合。它们都符合二元函数的形状，写起来不难，难的是想清楚顺序：reducer 会按框架给的顺序逐笔调用，先后不同结果可能不同。加法、拼接这类满足结合律的运算最安全；有依赖的运算最好先排序再合并。

## 六、三个坑：就地修改、重放和清空

第一个坑是就地修改。reducer 里写 `left.append(x)` 会改到框架持有的旧值，行为会随 checkpoint 和重放变得不可预测。写成 `left + [x]` 或 `[*left, x]`，永远返回新对象。

第二个坑跟重放有关：reducer 会在节点重跑时再执行一遍。所以 reducer 里不能有外部副作用——不能发请求、不能写库、不能打点。它应该是纯函数，同样的 left 和 right 永远得到同样的结果。这是"可重放"的底线，也是第 09 篇讲中断重放时会反复回到的前提。

第三个坑是清空。带合并语义的 reducer 收到空列表，语义是"并进去一个空列表"，原值还在。要真正清空或重置，用 `Overwrite`：

```python
from langgraph.types import Overwrite

def reset_hits(state: State):
    return {"hits": Overwrite([])}
```

`Overwrite` 直接绕过 reducer，把 channel 设成这个值。注意同一个 super-step 里，同一个 key 只允许一个 `Overwrite`，写两个照样报错。

还有一个不太直觉的地方：`graph.update_state` 这类人工改状态的操作，同样会走 reducer。你想覆盖某条历史消息，得用 `Overwrite`，否则就是又追加一遍。做时间回溯和人工修正时，这个差别很关键。

## 七、聚合就靠 reducer

map-reduce 的标准形状：一个节点拆任务，`Send` 扇出，worker 并行跑，最后汇总。汇总这一步，靠的就是列表 reducer。

```python
from langgraph.types import Send

def dispatch(state: State):
    return [Send("work", {"item": x}) for x in state["items"]]

class Overall(TypedDict):
    items: list[str]
    results: Annotated[list[dict], operator.add]
```

每个 worker 只返回自己那一份 `{"results": [r]}`，谁也不用等谁，最后由 reducer 串起来。这里的顺序由框架按 task path 决定，不保证等于业务顺序——要严格顺序，就在汇总节点里按 id 排一次。

这也是 reducer 真正的价值：它让"并行写"从冲突变成累积。列表、计数器、日志、候选答案池，都是这个模式。反过来说，如果某个字段你既想并行写又想保留"最新那个"，说明它不该是共享字段，要么拆 key，要么交给汇总节点统一裁决。

## 八、设计建议

- 默认覆盖够用，就别急着配 reducer；
- 消息一律 `add_messages`，别用 `operator.add` 凑合；
- 并行分支尽量写不同 key，把冲突在设计阶段消掉；
- 必须共享写时，reducer 要满足三条：不可变、幂等、可重放；
- 清空和重置用 `Overwrite`，别指望空值能把旧数据冲掉。

一句话收尾：reducer 决定的是"并发怎么写"，不是"数据长什么样"。画图时想不清谁写谁，就先别写代码。
