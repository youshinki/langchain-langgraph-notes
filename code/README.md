# code

每篇文章一个目录，编号与 `notes/` 对齐。每个目录都能单独跑，不依赖上一篇的产物。

```
01/
  loop_simulation.py   不需要任何依赖，用假模型跑一遍四步循环（可直接运行）
  agent_min.py         真实 create_agent 最小示例（需要 API key）
```

## 环境

```sh
python3.12 -m venv .venv && source .venv/bin/activate
pip install -U "langchain>=1.5,<2" "langgraph>=1.2,<2" "langchain-openai>=1.0"
```

模型统一通过 `init_chat_model` 接入，provider 由环境变量决定，不写死在代码里。

## 运行

```sh
python3 01/loop_simulation.py          # 离线，立刻有输出
OPENAI_API_KEY=... python3 01/agent_min.py
```

`loop_simulation.py` 是这个系列的地基：后面每一篇讲的能力，都是在它输出的那个消息列表上做文章。
