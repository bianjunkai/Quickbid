"""
QAAgent — 招标文件 Q&A

基于已解析数据（K01-K14 + 8 个模块 + 标记抽取）回答用户提问：
  - 单字段查询（get_k_field）
  - 模块列表 + 过滤（list_module）
  - 标记全文搜索（search_marker）
  - 整标摘要（get_overview）
  - 用户纠正 → 写入 K 字段（update_k_field）

多轮上下文：messages[] 全量入 context，LLM 看到自己的 tool_call 历史就能识别
"我之前问了 K03_招标人 → 用户说某公司 → 现在我应该 update_k_field" 的模式。

来源页：所有 K 字段查询返回 source_page，LLM 在文本答案里以 "(来源: P.N)" 形式呈现。
"""

import json
import logging
from typing import Any, Optional

from agents.base import BaseAgent, AgentContext
from agents.bid_parser.schema import (
    K01_K14_MAPPING,
    k_field_value,
    k_field_page,
    is_k_field_shaped,
    make_k_field,
)
from agents.bid_parser.pipeline import BidLLMClient

log = logging.getLogger(__name__)

# ============================================================
# K01-K14 字段清单（用于工具参数 enum）
# ============================================================

K_FIELD_KEYS = list(K01_K14_MAPPING.keys())  # ["K01_项目名称", ..., "K14_演示要求"]

MODULES = [
    "base",
    "qualification",
    "rejection",
    "scoring",
    "tech",
    "commercial",
    "templates",
    "logistics",
    "marker_extractions",
]

# 模块 → 数组字段映射（list_module 知道从哪取数组）
MODULE_LIST_FIELDS = {
    "qualification": "requirements",
    "rejection": "conditions",
    "scoring": "dimensions",
    "tech": "functional_requirements",
    "templates": "bid_doc_structure",
    "logistics": "originals_to_bring",
    "base": None,  # 标量对象，单独处理
    "commercial": None,  # 标量对象
    "marker_extractions": None,  # 多个优先级数组，特殊处理
}

# ============================================================
# Tool definitions（OpenAI 风格）
# ============================================================

TOOL_GET_K_FIELD = {
    "type": "function",
    "function": {
        "name": "get_k_field",
        "description": (
            "读取 K01-K14 某个字段的值。标量字段返回 value + source_page；"
            "数组字段（K10_星标项、K11_废标条款）返回 items + source_pages。"
            "适用：'项目名称/预算/截止时间' 等明确字段查询。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "enum": K_FIELD_KEYS,
                    "description": "K 字段 key，例如 'K01_项目名称' 或 'K04_预算金额'",
                }
            },
            "required": ["key"],
        },
    },
}

TOOL_LIST_MODULE = {
    "type": "function",
    "function": {
        "name": "list_module",
        "description": (
            "列出某模块下的条目。base/commercial 返回扁平对象；qualification/rejection/scoring/"
            "tech/templates 返回对应数组；logistics 返回 originals_to_bring。"
            "可传 filters 做精确过滤（如 {is_mandatory: true} 或 {severity: 'FATAL'}）。"
            "适用：'有哪些资质要求' / 'FATAL 级废标条款' / '评分维度' 等。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "module": {
                    "type": "string",
                    "enum": MODULES,
                    "description": "模块名",
                },
                "filters": {
                    "type": "object",
                    "description": (
                        "可选过滤，键值对必须完全匹配数组元素的字段。"
                        "例：{is_mandatory: true} 过滤强制资质；{severity: 'FATAL'} 过滤致命废标。"
                    ),
                },
            },
            "required": ["module"],
        },
    },
}

TOOL_SEARCH_MARKER = {
    "type": "function",
    "function": {
        "name": "search_marker",
        "description": (
            "在 marker_extractions 中按关键词全文搜索。"
            "适用：'有没有提到等保' / '★ 出现在哪些条款' / '搜索 XX'。"
            "返回匹配的 fatal/critical/high/medium/low 优先级条目，含原文 + source_page。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
            },
            "required": ["query"],
        },
    },
}

TOOL_GET_OVERVIEW = {
    "type": "function",
    "function": {
        "name": "get_overview",
        "description": (
            "返回 K01-K09 基本字段的摘要（项目名/编号/招标人/预算/截止/开标/评分/技术/资质）。"
            "适用：'这份标整体情况' / '先给我个全貌'。"
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

TOOL_UPDATE_K_FIELD = {
    "type": "function",
    "function": {
        "name": "update_k_field",
        "description": (
            "更新 K01-K14 某个字段的值。覆盖语义（会替换原值）。"
            "适用：用户明确纠正某字段，如 'K04 应该是 900 万' / '招标代理是某公司'。"
            "数类型字段（K04_预算金额）value 用数字；其他用字符串；"
            "K10/K11 数组用 string[]。"
            "写入后会在响应里返回 updated_fields 列表，由系统落库到 Project.parsed_data + Project 物化字段。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "enum": K_FIELD_KEYS,
                    "description": "K 字段 key",
                },
                "value": {
                    "description": (
                        "新值。标量字段传字符串或数字（按字段语义）；"
                        "K10/K11 数组字段传 string 数组。"
                    ),
                },
            },
            "required": ["key", "value"],
        },
    },
}

TOOLS = [
    TOOL_GET_K_FIELD,
    TOOL_LIST_MODULE,
    TOOL_SEARCH_MARKER,
    TOOL_GET_OVERVIEW,
    TOOL_UPDATE_K_FIELD,
]

# ============================================================
# System prompt
# ============================================================

SYSTEM_PROMPT = """你是招标文件的 Q&A 助手，基于已解析的标书数据回答用户问题。

## 角色与限制
- 只能基于已解析的 parsed_data 回答，不提供分析、建议或推断（用户明确不要建议）
- 找不到答案时，**必须**主动问用户要，不要编造
- 每个事实回答都必须带来源页码（source_page）
- 简洁、专业、像投标经理在回答问题

## 工具使用指南
- 询问单个 K 字段（"项目名称"/"预算"/"截止时间"）→ get_k_field
- 询问模块列表（"有哪些资质要求"/"FATAL 级废标"）→ list_module，可传 filters
- 询问某关键词是否在原文中提及（"有没有提到等保"/"搜索 XX"）→ search_marker
- 询问整体情况（"这份标整体情况"）→ get_overview
- 用户纠正某字段值（"K04 应该是 900 万"）→ update_k_field 写入

## 多轮 / 自纠正流程
- 你会拿到完整对话历史 messages[]
- 如果你上轮用了 get_k_field 拿到 null/缺失 → 你应该自然地反问用户，例如：
  "招标代理信息在解析数据中未提取，你可以告诉我吗？"
- 用户下一轮如果直接给值（"是某公司"）→ 你应该看到历史，调 update_k_field 写入，再回 "已更新：K03_招标人 = 某公司"
- 字段值是数组（K10/K11）时，整条替换

## 答案格式
- 简洁，1-3 句话
- 数据类回答带页码："项目预算 165 万元（来源：P.12）"
- 列表类回答可以编号列出
- 字段值是 "未找到"/null 时说 "该信息在解析数据中未提取，你可以告诉我吗？"
- 字段已更新时："已更新：K04_预算金额 = 900 万元"
- 跨章问题不在数据范围（"明天天气"）→ "该问题不在已解析的标书数据范围内，我无法回答"

## 解析数据为空时
如果所有 get_k_field/list_module 返回的 found=false（parsed_data 整体为空），
告诉用户"暂无已解析数据，请先上传并解析招标文件"。
"""


# ============================================================
# QAAgent
# ============================================================

class QAAgent(BaseAgent):
    """基于已解析数据的 Q&A agent。"""

    name = "qa"
    description = "基于已解析数据回答用户提问，支持多轮与用户纠正写入"
    system_prompt = SYSTEM_PROMPT
    temperature = 0.0

    MAX_TOOL_ITERATIONS = 3

    def __init__(self, config: dict | None = None):
        super().__init__()
        self.config = config or {}
        self._llm: Optional[BidLLMClient] = None

    def _get_llm(self) -> BidLLMClient:
        if self._llm is None:
            ai = self.config.get("ai", {})
            self._llm = BidLLMClient(
                model=ai.get("model", "deepseek-chat"),
                base_url=ai.get("base_url", "https://api.deepseek.com"),
            )
        return self._llm

    # ================================================================
    # 主入口
    # ================================================================

    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        parsed_data = ctx.parsed_data or {}
        chat_messages = ctx.chat_messages or []

        # 把 AI SDK 格式 → OpenAI 格式（已转换则原样使用）
        messages = ai_sdk_to_openai(chat_messages) if chat_messages else []
        if not messages:
            # 兼容老调用：仅 user_input
            if ctx.user_input:
                messages = [{"role": "user", "content": ctx.user_input}]
            else:
                return {
                    "text": "（无用户输入）",
                    "tool_calls_made": [],
                    "updated_fields": [],
                }

        # 解析数据空就提前返
        if not parsed_data:
            return {
                "text": "暂无已解析数据，请先上传并解析招标文件。",
                "tool_calls_made": [],
                "updated_fields": [],
            }

        llm = self._get_llm()
        if not llm.is_available:
            return {
                "text": "LLM 不可用（缺 TENDER_DEEPSEEK_API_KEY），无法回答。",
                "tool_calls_made": [],
                "updated_fields": [],
            }

        # 注入 system prompt
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        tool_calls_made: list[dict] = []
        updated_fields: list[dict] = []

        for iteration in range(self.MAX_TOOL_ITERATIONS):
            result = llm.chat_with_tools(messages=full_messages, tools=TOOLS)
            if result is None:
                return {
                    "text": "LLM 调用失败（无响应）。",
                    "tool_calls_made": tool_calls_made,
                    "updated_fields": updated_fields,
                }
            if "error" in result:
                return {
                    "text": f"LLM 调用失败：{result['error']}",
                    "tool_calls_made": tool_calls_made,
                    "updated_fields": updated_fields,
                }

            tool_calls = result.get("tool_calls") or []
            if not tool_calls:
                # 终态：text 响应
                return {
                    "text": (result.get("content") or "").strip(),
                    "tool_calls_made": tool_calls_made,
                    "updated_fields": updated_fields,
                }

            # 推 assistant 消息（含 tool_calls）
            full_messages.append({
                "role": "assistant",
                "content": result.get("content") or "",
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                        },
                    }
                    for tc in tool_calls
                ],
            })

            # 执行工具 + 推 tool 结果
            for tc in tool_calls:
                tool_result = self._execute_tool(tc["name"], tc["arguments"], parsed_data)
                tool_calls_made.append({
                    "tool": tc["name"],
                    "args": tc["arguments"],
                    "result": tool_result,
                })
                if tc["name"] == "update_k_field" and tool_result.get("updated"):
                    updated_fields.append({
                        "key": tc["arguments"].get("key"),
                        "new_value": tc["arguments"].get("value"),
                    })
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

        return {
            "text": "已达到最大工具调用轮次。",
            "tool_calls_made": tool_calls_made,
            "updated_fields": updated_fields,
        }

    # ================================================================
    # 工具执行器
    # ================================================================

    def _execute_tool(self, name: str, args: dict, parsed_data: dict) -> dict:
        try:
            if name == "get_k_field":
                return self._get_k_field(parsed_data, args.get("key"))
            if name == "list_module":
                return self._list_module(parsed_data, args.get("module"), args.get("filters") or {})
            if name == "search_marker":
                return self._search_marker(parsed_data, args.get("query", ""))
            if name == "get_overview":
                return self._get_overview(parsed_data)
            if name == "update_k_field":
                return self._update_k_field(parsed_data, args.get("key"), args.get("value"))
            return {"error": f"未知工具：{name}"}
        except Exception as e:
            log.exception("tool %s failed", name)
            return {"error": f"{type(e).__name__}: {e}"}

    def _get_k_field(self, parsed_data: dict, key: str) -> dict:
        if not key or key not in parsed_data:
            return {"found": False, "key": key, "value": None, "source_page": None}
        field = parsed_data[key]
        return {
            "found": True,
            "key": key,
            "value": k_field_value(field),
            "source_page": k_field_page(field),
        }

    def _list_module(self, parsed_data: dict, module: str, filters: dict) -> dict:
        if not module or module not in parsed_data:
            return {"found": False, "module": module, "items": []}
        mod = parsed_data[module]
        if not isinstance(mod, dict):
            return {"found": False, "module": module, "items": [], "error": "module 数据非对象"}

        list_field = MODULE_LIST_FIELDS.get(module)
        if module == "base" or module == "commercial":
            # 标量对象：原样返回，可按 filters 精确匹配顶层字段
            items = dict(mod)
            if filters:
                items = {k: v for k, v in items.items() if all(items.get(fk) == fv for fk, fv in filters.items())}
                # 过滤后如果不是空 dict，就保留为单条
                items = [items] if items else []
            else:
                # 转成 [{"field": "project_name", "value": "..."}] 形式便于展示
                items = [{"field": k, "value": v} for k, v in mod.items()]
            return {"found": True, "module": module, "total": len(items), "items": items}
        if module == "marker_extractions":
            # 聚合所有优先级
            agg = []
            for prio in ("fatal_items", "critical_items", "high_items", "medium_items", "low_items"):
                for it in mod.get(prio, []):
                    if not isinstance(it, dict):
                        continue
                    item = dict(it)
                    item["priority"] = prio
                    agg.append(item)
            return self._filter_items("marker_extractions", agg, filters)
        if list_field:
            items = mod.get(list_field, []) or []
            return self._filter_items(module, items, filters)

        return {"found": True, "module": module, "items": mod}

    def _filter_items(self, module: str, items: list, filters: dict) -> dict:
        if filters:
            items = [it for it in items if isinstance(it, dict) and all(it.get(k) == v for k, v in filters.items())]
        return {"found": True, "module": module, "total": len(items), "items": items}

    def _search_marker(self, parsed_data: dict, query: str) -> dict:
        if not query:
            return {"query": "", "total": 0, "matches": []}
        markers = parsed_data.get("marker_extractions", {})
        if not isinstance(markers, dict):
            return {"query": query, "total": 0, "matches": []}
        q = query.lower()
        matches = []
        for prio in ("fatal_items", "critical_items", "high_items", "medium_items", "low_items"):
            for it in markers.get(prio, []):
                if not isinstance(it, dict):
                    continue
                text = (it.get("raw_text") or "") + " " + (it.get("semantic") or "")
                if q in text.lower():
                    matches.append({
                        "priority": prio,
                        "marker": it.get("marker"),
                        "source_page": it.get("source_page"),
                        "text": (it.get("raw_text") or it.get("semantic") or "")[:200],
                    })
        return {"query": query, "total": len(matches), "matches": matches}

    def _get_overview(self, parsed_data: dict) -> dict:
        overview = {}
        for i in range(1, 10):  # K01-K09
            prefix = f"K{i:02d}_"
            for fk in parsed_data:
                if fk.startswith(prefix):
                    overview[fk] = {
                        "value": k_field_value(parsed_data[fk]),
                        "source_page": k_field_page(parsed_data[fk]),
                    }
                    break
        return overview

    def _update_k_field(self, parsed_data: dict, key: str, value: Any) -> dict:
        if not key or not key.startswith("K") or "_" not in key:
            return {"updated": False, "error": f"无效的 K 字段：{key}"}
        if key not in parsed_data:
            return {"updated": False, "error": f"字段不存在：{key}"}
        # K10/K11 数组字段
        is_array = key in ("K10_星标项", "K11_废标条款")
        if is_array and not isinstance(value, list):
            return {"updated": False, "error": f"{key} 应为字符串数组"}

        old_value = k_field_value(parsed_data[key])
        parsed_data[key] = make_k_field(value, source_page=None)
        return {
            "updated": True,
            "key": key,
            "old_value": old_value,
            "new_value": value,
        }


# ============================================================
# AI SDK messages → OpenAI messages 转换
# ============================================================

def ai_sdk_to_openai(messages: list[dict]) -> list[dict]:
    """把前端 useChat 的 messages[]（AI SDK v3 格式）转成 OpenAI Chat 格式。

    AI SDK v3:
      { role: "user"|"assistant"|"system", parts: [{type: "text", text: "..."}, ...] }
    AI SDK v2:
      { role: ..., content: "..." | [{type: "text", text: "..."}] }
    OpenAI:
      { role: ..., content: "..." }
      + assistant 可选 tool_calls；tool 角色用于工具结果（这里不需要手动构造）
    """
    out = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role not in ("user", "assistant", "system"):
            continue
        text = _extract_ai_sdk_text(m)
        if text is None:
            continue
        out.append({"role": role, "content": text})
    return out


def _extract_ai_sdk_text(m: dict) -> Optional[str]:
    # v3 parts
    parts = m.get("parts")
    if isinstance(parts, list) and parts:
        texts = [p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") in ("text", None)]
        joined = "".join(texts)
        if joined:
            return joined
    # v2 content
    content = m.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
        )
    return None
