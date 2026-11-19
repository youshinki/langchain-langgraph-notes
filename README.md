# langchain-langgraph-notes

**LangChain 1.x / LangGraph 实战系列**的配套仓库：每篇文章对应的可运行代码、配图源文件、可复现步骤都放在这里。

> 头条系列名：《把 Agent 画成图：LangChain 1.x 与 LangGraph 实战》
> 头条合集标题：**把 Agent 画成图：18 篇吃透 LangChain 与 LangGraph**
> 合集封面：`assets/00/00-cover-16x9.png`（16:9，深色科技风）

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

## 在线文档（飞书知识库）

知识库名：**LangChain / LangGraph 实战**（space_id `7709512825424579611`）

| 文档 | 链接 |
|---|---|
| 系列总览（18 篇目录与进度） | https://my.feishu.cn/wiki/IuziwwHkIiUOlCkfhDtcWyQ6nTe |
| 第 01 篇：开篇 | https://my.feishu.cn/wiki/KqzowWFQMiuPHOkzwVIcWZfsnyd |

文档正文由仓库 markdown 转 XML 生成，三张配图按章节内嵌；后续每写完一篇，按同样流程建文档、移入知识库，并在总览表里把状态改为「已发布」。

装环境：

```sh
python3.12 -m venv .venv && source .venv/bin/activate
pip install -U "langchain>=1.5,<2" "langgraph>=1.2,<2" "langchain-openai>=1.0"
```

模型接入不绑定厂商，代码里统一走 `init_chat_model`，换 provider 只改一行。

## 系列目录（共 18 篇，四个阶段）

发布标题统一为 `第XX篇：主标题｜Agent画图`，控制在 30 字以内；`Agent画图` 是合集《把 Agent 画成图》的简称，便于在文章列表里一眼认出系列。

### 一、LangChain 1.x 重做之后（01-05）

| # | 发布标题 | 核心问题 | 状态 |
|---|---|---|---|
| 01 | LangChain 只剩一个函数 | 删了什么、为什么敢删、代价在哪 | 初稿（含 3 张配图） |
| 02 | 消息列表多了什么 | agent loop 每次迭代在状态上留下什么 | 待写 |
| 03 | 四个钩子位怎么用 | before/after/wrap_model/wrap_tool 的边界 | 待写 |
| 04 | 工具怎么被模型看见 | schema 投影、ToolStrategy 与 ProviderStrategy | 待写 |
| 05 | 模型层怎么不写死 | 多 provider 统一、按任务选模型、失败切备 | 待写 |

### 二、LangGraph 运行时（06-11）

| # | 发布标题 | 核心问题 | 状态 |
|---|---|---|---|
| 06 | State 怎么合并 | 并行节点写同一个 key 为什么不打架 | 待写 |
| 07 | 一张图怎么分叉 | 条件边、Command、Send 与 map-reduce | 待写 |
| 08 | 断点续跑续在哪 | checkpointer、thread、super-step | 待写 |
| 09 | 中断为什么要重放 | interrupt 的真实语义与幂等写法 | 待写 |
| 10 | 流式到底流什么 | stream modes 与 v2/v3 事件协议 | 待写 |
| 11 | 子图怎么隔上下文 | supervisor、handoff 与上下文隔离 | 待写 |

### 三、工程化（12-15）

| # | 发布标题 | 核心问题 | 状态 |
|---|---|---|---|
| 12 | 回到上一步重走 | 历史状态、get_state_history 与 fork | 待写 |
| 13 | 重试超时怎么配 | 重试、节点超时、error_handler、优雅停机 | 待写 |
| 14 | 线上怎么看得清 | trace 里看什么、回归集怎么建 | 待写 |
| 15 | 从脚本到服务 | Agent Server、线程与定时任务 | 待写 |

### 四、实战（16-18）

| # | 发布标题 | 核心问题 | 状态 |
|---|---|---|---|
| 16 | 带人审的资料 Agent | 串起 03/08/09/10 | 待写 |
| 17 | 多 Agent 研究小组 | supervisor + 子图，串起 07/11/13 | 待写 |
| 18 | 四种编排怎么选 | LangChain / LangGraph / Deep Agents / dsh | 待写 |

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
