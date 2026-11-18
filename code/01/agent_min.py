"""第01篇配套：LangChain 1.5 的最小 create_agent。

需要：
    pip install -U "langchain>=1.5,<2" "langchain-openai>=1.0"

环境变量按你的 provider 填：
    export OPENAI_API_KEY=...
    export OPENAI_BASE_URL=https://api.deepseek.com/v1   # 以 DeepSeek 为例

运行：
    python3 agent_min.py
"""

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool


@tool
def search_docs(query: str) -> str:
    """检索内部文档，返回与 query 最相关的片段。"""
    # 第 01 篇只验证循环，这里用假数据；第 04 篇接真的检索。
    return (
        "LangGraph 1.2 的三处改动：DeltaChannel 只存增量；"
        "add_node 支持 timeout；error_handler 可在重试耗尽后接管。"
    )


def main() -> None:
    model = init_chat_model("openai:gpt-4.1-mini")   # 换 provider 只改这一行
    agent = create_agent(
        model=model,
        tools=[search_docs],
        system_prompt="先查资料再回答；查不到就说查不到。",
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": "LangGraph 1.2 改了什么？"}]}
    )

    for m in result["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    main()
