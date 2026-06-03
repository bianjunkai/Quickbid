"""
AI SDK Data Stream Protocol — Python 实现

Vercel AI SDK 在前端 useChat 期望一种特定的 SSE 事件格式（"AI SDK Data Stream Protocol"）。
详见 https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#data-stream-protocol

事件类型（仅用到的子集）：
- start              — 流开始
- text-start         — 文本片段开始
- text-delta         — 文本片段增量
- text-end           — 文本片段结束
- tool-input-available  — 工具调用输入
- tool-output-available — 工具调用输出
- finish-step        — 当前步骤完成
- finish             — 整个流结束
- error              — 错误

注：v3 协议**没有** `finish-message` 事件 — 消息边界由 `start` / `finish` 标记。
每条事件通过 SSE 发送：`data: {json}\n\n`
"""
import json
import uuid
from typing import Any, AsyncIterator, Optional


def _new_id(prefix: str = "msg") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def aiter_sse(data: dict | str) -> AsyncIterator[dict]:
    """单条 SSE 事件的最小封装（sse_starlette.EventSourceResponse 消费 AsyncIterator[dict]）。"""
    if isinstance(data, dict):
        data = json.dumps(data, ensure_ascii=False)
    yield {"data": data}


async def stream_text(
    text: str,
    message_id: Optional[str] = None,
    text_id: Optional[str] = None,
) -> AsyncIterator[dict]:
    """
    发送一个完整的 text 段（简化为单条 text-delta）。

    协议：start → text-start → text-delta → text-end → finish-step
    """
    message_id = message_id or _new_id("msg")
    text_id = text_id or _new_id("text")
    yield {"data": json.dumps({"type": "start", "messageId": message_id}, ensure_ascii=False)}
    yield {"data": json.dumps({"type": "text-start", "id": text_id}, ensure_ascii=False)}
    yield {"data": json.dumps({"type": "text-delta", "id": text_id, "delta": text}, ensure_ascii=False)}
    yield {"data": json.dumps({"type": "text-end", "id": text_id}, ensure_ascii=False)}
    yield {"data": json.dumps({"type": "finish-step"}, ensure_ascii=False)}


async def stream_tool_call(
    tool_name: str,
    tool_input: dict,
    tool_output: Any,
    message_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
) -> AsyncIterator[dict]:
    """
    发送一个工具调用 + 输出（前端 useChat 的 tool UI 由此触发）。

    协议：start → tool-input-available → tool-output-available → finish-step
    """
    message_id = message_id or _new_id("msg")
    tool_call_id = tool_call_id or _new_id("call")
    yield {"data": json.dumps({"type": "start", "messageId": message_id}, ensure_ascii=False)}
    yield {"data": json.dumps(
        {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input},
        ensure_ascii=False,
    )}
    yield {"data": json.dumps(
        {"type": "tool-output-available", "toolCallId": tool_call_id, "output": tool_output},
        ensure_ascii=False,
    )}
    yield {"data": json.dumps({"type": "finish-step"}, ensure_ascii=False)}


async def stream_finish(message_id: Optional[str] = None) -> AsyncIterator[dict]:
    """发送 finish 事件。"""
    yield {"data": json.dumps({"type": "finish"}, ensure_ascii=False)}


async def stream_error(error_message: str) -> AsyncIterator[dict]:
    """发送 error 事件。"""
    yield {"data": json.dumps({"type": "error", "errorText": error_message}, ensure_ascii=False)}
