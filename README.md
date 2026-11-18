# langchain-langgraph-notes

**LangChain 1.x / LangGraph 实战系列**的配套仓库：每篇文章对应的可运行代码、配图源文件、可复现步骤都放在这里。

> 头条系列名：《把 Agent 画成图：LangChain 1.x 与 LangGraph 实战》

## 这个系列想解决什么问题

讲 LangChain 的文章很多，但大多停在「装包、调 create_agent、跑通」这一步。真正让人卡住的是三件事：

1. **版本断层**。1.0 之后主包几乎被重写，网上大量教程还是 `LLMChain` + `AgentExecutor` 那套，照着抄直接报错。
2. **抽象变薄之后，定制没有地方放**。链没了，`create_agent` 只给一个函数，想加人审、加摘要、加路由，得知道钩子挂在哪。
3. **图跑起来之后不可控**。状态怎么合并、中断为什么重放整个节点、断点续跑丢不丢写、子图上下文怎么隔离——这些只在文档角落写了一句。

所以本系列的写法是：**先给结论，再给最小可运行代码，最后说清边界（什么时候不该这么写）。**

## 版本锚定

LangChain 生态迭代快，本仓库所有文章锁定在同一组版本上：

| 项 | 值 |
|---|---|
| Python | 3.11+（`langchain` 1.5 起不再支持 3.10） |
| langchain | 1.5.0 |
| langchain-core | 1.8.x |
| langgraph | 1.2.x |
| deepagents | 0.7.x（仅第 18 篇对比时涉及） |
| 锚定日期 | 2026-11-18 |

装环境：

```sh
python3.12 -m venv .venv && source .venv/bin/activate
pip install -U "langchain>=1.5,<2" "langgraph>=1.2,<2" "langchain-openai>=1.0"
```

模型接入不绑定厂商，代码里统一走 `init_chat_model`，换 provider 只改一行。

## 系列目录（共 18 篇，四个阶段）

### 一、LangChain 1.x 重做之后（01-05）

| # | 标题 | 核心问题 | 状态 |
|---|---|---|---|
| 01 | 开篇：LangChain 1.x 只留了一个 create_agent | 删了什么、为什么敢删、代价在哪 | 初稿（含 3 张配图） |
| 02 | 转一圈：消息列表里到底多了什么 | agent loop 的每一次迭代在状态上留下什么 | 待写 |
| 03 | middleware：四个钩子位能塞什么 | before/after/wrap_model/wrap_tool 的边界 | 待写 |
| 04 | 工具与结构化输出 | schema 怎么被投影给模型、ToolStrategy 与 ProviderStrategy | 待写 |
| 05 | 模型层：content blocks、路由与降级 | 多 provider 统一、按任务选模型、失败切备 | 待写 |

### 二、LangGraph 运行时（06-11）

| # | 标题 | 核心问题 | 状态 |
|---|---|---|---|
| 06 | StateGraph 三件套：State、Reducer、Channel | 并行节点写同一个 key 为什么不打架 | 待写 |
| 07 | 控制流：条件边、Command、Send | 一对多分发与 map-reduce | 待写 |
| 08 | 持久化：checkpointer、thread、super-step | 断点续跑到底续在哪一步 | 待写 |
| 09 | interrupt：为什么恢复时要重放整个节点 | 中断的真实语义与幂等写法 | 待写 |
| 10 | 流式：stream modes 与 v2/v3 事件协议 | token、更新、工具参数增量怎么取 | 待写 |
| 11 | 子图与多 Agent：supervisor、handoff | 上下文共享与隔离的边界 | 待写 |

### 三、工程化（12-15）

| # | 标题 | 核心问题 | 状态 |
|---|---|---|---|
| 12 | 时间旅行：历史状态与 fork | 回退一步、走另一条路 | 待写 |
| 13 | 可靠性：重试、节点超时、error_handler、优雅停机 | 1.2 新增的四个控制点怎么配 | 待写 |
| 14 | 可观测与评估 | trace 里看什么、回归集怎么建 | 待写 |
| 15 | 部署：Agent Server、线程与定时任务 | 从脚本到可托管服务 | 待写 |

### 四、实战（16-18）

| # | 标题 | 核心问题 | 状态 |
|---|---|---|---|
| 16 | 实战：一个带人审的资料整理 Agent | 串起 03/08/09/10 | 待写 |
| 17 | 实战：supervisor + 子图的研究小组 | 串起 07/11/13 | 待写 |
| 18 | 复盘：LangChain / LangGraph / Deep Agents / dsh 怎么选 | 四种编排取舍 | 待写 |

## 目录结构

```
notes/      每篇一篇 markdown，命名 01-xxx.md，正文顶部标版本锚定
assets/     每篇 3 张 1:1 配图，按篇号分目录
code/       每篇可独立运行的最小示例，按篇号分目录
diagrams/   结构图源文件（drawio / mermaid）
```

## 写作约定

- 每篇正文约 2000 字，一段 2-4 行，不堆砌概念。
- 每个结论后面跟一段「边界」：这个写法什么时候不适用。
- 代码必须能单独跑，不依赖上一篇的中间状态。
- 引用官方文档时给链接与日期；版本相关的内容标注具体版本号。

## 关于作者

杨振辉（youshinki），XR / 音视频全栈架构师。前两个系列：

- [ai-agent-zero-to-hero](https://github.com/youshinki/ai-agent-zero-to-hero)（75 篇，AI Agent 从零到商业化）
- [dsh-source-notes](https://github.com/youshinki/dsh-source-notes)（15 篇，DeepSeek Harness 源码拆解）
