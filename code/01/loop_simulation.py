"""第01篇配套：不装任何依赖，用假模型跑一遍 Agent 的四步循环。

目的不是演示框架，是把 create_agent 底下那件事摊开：
    送消息 -> 模型回 tool_calls -> 执行工具并回填 -> 再送 -> 直到没有工具调用

运行：
    python3 loop_simulation.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Message:
    role: str                      # user / assistant / tool
    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)   # 只有 assistant 会有
    tool_call_id: str = ""         # 只有 tool 会有


class FakeModel:
    """按剧本返回：第一次要工具，第二次给答案。

    真实模型的差别只在于它自己决定要不要调工具，循环结构完全一样。
    """

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, messages: list[Message]) -> Message:
        self.calls += 1
        if self.calls == 1:
            return Message(
                role="assistant",
                content="我先查一下资料。",
                tool_calls=[{
                    "id": "call_001",
                    "name": "search_docs",
                    "args": {"query": "LangGraph 1.2 新特性"},
                }],
            )
        return Message(role="assistant", content="整理完了：1.2 的主线是节点级控制。")


def search_docs(query: str) -> str:
    """假装检索，返回一段结构化文本。"""
    return json.dumps(
        {"query": query, "hits": ["DeltaChannel 只存增量", "add_node 支持 timeout", "error_handler 可路由"]},
        ensure_ascii=False,
    )


TOOLS: dict[str, Callable[..., str]] = {"search_docs": search_docs}


def agent_loop(question: str, model: FakeModel, max_steps: int = 8) -> list[Message]:
    """四步循环的最小实现。"""

    messages: list[Message] = [Message(role="user", content=question)]

    for step in range(1, max_steps + 1):
        print(f"\n=== step {step}：把 {len(messages)} 条消息送给模型 ===")

        reply = model(messages)
        messages.append(reply)
        print(f"模型返回：content={reply.content!r} tool_calls={len(reply.tool_calls)} 个")

        # 第四步的出口：不再调工具，循环结束
        if not reply.tool_calls:
            print("没有工具调用，循环结束。")
            return messages

        for call in reply.tool_calls:
            name = call["name"]
            fn = TOOLS[name]
            result = fn(**call["args"])
            messages.append(
                Message(role="tool", content=result, tool_call_id=call["id"])
            )
            print(f"执行工具 {name}({call['args']}) -> {result[:40]}…")

    raise RuntimeError("步数超限：真实系统里这一步通常交给 max_iterations 或超时策略")


if __name__ == "__main__":
    final = agent_loop("LangGraph 1.2 改了什么？", FakeModel())

    print("\n=== 最终消息列表 ===")
    for i, m in enumerate(final):
        extra = f" tool_calls={len(m.tool_calls)}" if m.tool_calls else ""
        extra += f" tool_call_id={m.tool_call_id}" if m.tool_call_id else ""
        print(f"{i:>2} {m.role:<9} {m.content[:50]}{extra}")
