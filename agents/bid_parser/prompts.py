"""
LLM Prompt 模板 — 五步管道的所有 LLM 调用。

从 bid-parse skill 的 SKILL.md 中提取并适配。
每个 prompt 函数接受文本/数据参数，返回标准的 messages 列表。
"""

import json
from agents.bid_parser.schema import BID_MODULE_DESCRIPTIONS, DEFAULT_MARKERS, SYMBOL_ALIASES

# ============================================================
# 通用角色设定
# ============================================================

ROLE_EXPERT = "你是招标文件结构化解析专家。你的任务是从招标文件原文中精准提取信息，严格按指定 JSON 格式输出。不编造、不推测，找不到的字段明确标注。"

# ============================================================
# Step 2: 标记语义识别
# ============================================================

MARKER_SEMANTICS_SYSTEM = """你是招标文件分析专家。请通读以下招标文件全文。

## 任务
识别文件中所有特殊标记符号（三角形、五角星、菱形、圆形、对勾、方框、加粗文本等），结合上下文推断每个标记的含义。

## 输出格式
严格按照以下 JSON 格式输出：
```json
{
  "detection": {
    "total_marker_types_found": <int>,
    "markers": [
      {
        "symbol": "<标记符号，如 ▲>",
        "unicode": "<Unicode 码点，如 U+25B2>",
        "occurrence_count": <int>,
        "semantic_label": "<简短概括，如'核心技术要求'>",
        "semantic_detail": "<完整语义解释，结合上下文>",
        "priority": "FATAL|CRITICAL|HIGH|MEDIUM|LOW",
        "action": "<针对该标记内容的处理建议>",
        "maps_to_field": "<映射到的目标字段路径，如 tech.functional_requirements>"
      }
    ]
  }
}
```

## 优先级定义
- FATAL：显式废标标记，出现即废标
- CRITICAL：缺则废标的强制条件
- HIGH：严重扣分项
- MEDIUM：一般影响的条款
- LOW：参考信息

## 重要
- 标记符号可能包括但不限于：▲△★☆●○◇◆※✓✔☑■□◎
- 同一个符号在不同章节可能有不同含义，请结合上下文判断
- 只输出 JSON，不要有其他文字。"""


def marker_semantics_messages(full_text: str) -> list[dict]:
    """Step 2: 标记语义识别 prompt。将全文送 LLM。"""
    # 截取前 30000 字符以避免 context 溢出（足够覆盖标记语义分析）
    text_snippet = full_text[:30000]
    if len(full_text) > 30000:
        text_snippet += f"\n\n... [全文共 {len(full_text)} 字符，已截断]"

    return [
        {"role": "system", "content": MARKER_SEMANTICS_SYSTEM},
        {"role": "user", "content": f"以下是招标文件全文，请识别所有特殊标记符号的语义：\n\n{text_snippet}"},
    ]


# ============================================================
# Step 3: 标记精准抽取
# ============================================================

MARKER_EXTRACTION_SYSTEM = """你是招标文件标记内容抽取专家。

## 任务
以下是招标文件中 {semantic_label}（{symbol}）标记的 {count} 处内容。
请将每处内容抽取为结构化字段，映射到 target_field_path。

## 输出格式
```json
[
  {{
    "marker": "{symbol}",
    "id": "<编号，如 {symbol}001>",
    "semantic": "{semantic_label}",
    "raw_text": "<标记对应的原文（完整保留）>",
    "source_page": <页码>,
    "source_line": "<所在段落/行号>",
    "mapped_to": {{
      "field_path": "<目标字段路径>"
    }},
    "compliance_action": "<投标方应如何响应该标记内容>"
  }}
]
```

## 要求
- 每条信息必须带 source_page
- 原文必须完整保留，不省略
- compliance_action 要具体可操作
- 只输出 JSON 数组，不要有其他文字"""


def marker_extraction_messages(
    marker_symbol: str,
    semantic_label: str,
    priority: str,
    target_field: str,
    hits: list[dict],
) -> list[dict]:
    """Step 3: 单批标记抽取 prompt。"""
    system = MARKER_EXTRACTION_SYSTEM.format(
        semantic_label=semantic_label,
        symbol=marker_symbol,
        count=len(hits),
    )

    # 构建命中列表文本
    hits_text_parts = []
    for i, h in enumerate(hits, 1):
        hits_text_parts.append(
            f"[{i}] 页码 {h['page']} | 行文：{h['line_text']}\n"
            f"    上下文：{h['context']}"
        )
    hits_text = "\n\n".join(hits_text_parts)

    user = (
        f"标记符号：{marker_symbol}\n"
        f"语义标签：{semantic_label}\n"
        f"优先级：{priority}\n"
        f"目标字段路径：{target_field}\n\n"
        f"以下是该标记在全文中的 {len(hits)} 处出现：\n\n{hits_text}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


# ============================================================
# Step 4: 主体字段分段抽取
# ============================================================

EXTRACTION_SYSTEM_TEMPLATE = """你是招标文件结构化解析专家。

## 任务
从以下招标文件章节原文中提取 **{module_name}** 信息。

## 输出约束
请以 JSON 格式输出，包含以下字段：
{field_list}

## 要求
- 每条信息必须带 `source_page`（整数，来源页码）
- 如果信息来源于特殊标记，必须带 `source_marker` 对象：{{"symbol": "<标记符号>", "marker_id": "<标记ID>"}}
- 原文中没有的信息，标注为 null 或空数组（不要编造）
- 逐条列出，不要遗漏
- 只输出 JSON，不要有其他文字"""


def extraction_messages(
    module_key: str,
    chapter_text: str,
    marker_context: str = "",
) -> list[dict]:
    """
    Step 4: 单模块分段抽取 prompt。

    Args:
        module_key: 模块名（base/qualification/rejection/scoring/tech/commercial/templates/logistics）
        chapter_text: 对应章节原文
        marker_context: 已抽取的标记数据（JSON 字符串，可选）
    """
    module_info = BID_MODULE_DESCRIPTIONS.get(module_key, {})
    module_name = module_info.get("description", module_key)
    fields = module_info.get("key_fields", [])

    field_list = "\n".join(f"  - {f}" for f in fields)
    system = EXTRACTION_SYSTEM_TEMPLATE.format(
        module_name=module_name,
        field_list=field_list,
    )

    user_parts = [f"## 招标文件 {module_name} 相关章节原文\n\n{chapter_text}"]

    if marker_context:
        user_parts.append(
            f"\n\n## 已抽取的标记数据（请合并到对应字段）\n\n{marker_context}"
        )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


# ============================================================
# Step 5: 合并校验
# ============================================================

VALIDATION_SYSTEM = """你是招标文件解析质量审核专家。

## 任务
检查以下解析结果的完整性，发现：
1. marker_extractions 中的条目是否都已映射到对应目标字段
2. 数值类信息在不同字段中是否一致（如同一金额、同一日期）
3. 必填字段是否都已填充
4. 正则命中总数 vs 映射数是否一致

## 输出格式
```json
{
  "validation_passed": <bool>,
  "issues": [
    {
      "severity": "error|warning|info",
      "type": "<问题类型>",
      "field": "<相关字段路径>",
      "description": "<问题描述>",
      "suggestion": "<修复建议>"
    }
  ],
  "risk_summary": {
    "fatal_count": <int>,
    "critical_count": <int>,
    "missing_fields": ["<字段路径>", ...],
    "inconsistencies": [
      {"fields": ["<字段A>", "<字段B>"], "description": "<不一致描述>"}
    ],
    "estimated_score_range": {"min": <float>, "max": <float>, "total": <float>}
  }
}
```

## 要求
- 仔细逐条核对
- 只输出 JSON"""


def validation_messages(
    full_result: dict,
    marker_summary: dict,
) -> list[dict]:
    """Step 5: 合并校验 prompt。"""
    user = (
        f"## 解析结果\n\n{json.dumps(full_result, ensure_ascii=False, indent=2)}\n\n"
        f"## 标记扫描统计\n\n{json.dumps(marker_summary, ensure_ascii=False, indent=2)}\n\n"
        "请核对以上解析结果，输出校验报告。"
    )

    return [
        {"role": "system", "content": VALIDATION_SYSTEM},
        {"role": "user", "content": user},
    ]


# ============================================================
# 快速模式 (K01-K14)
# ============================================================

QUICK_EXTRACTION_SYSTEM = """你是招标文件分析专家。请从以下招标文件内容中提取关键信息。

返回严格的 JSON 格式，包含以下字段：
- K01_项目名称: string
- K02_招标编号: string
- K03_招标人: string
- K04_预算金额: string (含单位)
- K05_投标截止时间: string (ISO 8601)
- K06_开标时间: string (ISO 8601)
- K07_评分标准: string (简要概括评分方法、权重、主要维度)
- K08_技术要求: string (简要概括涉及的系统模块和技术栈)
- K09_商务资质要求: string (列出关键资质/业绩/人员/财务要求)
- K10_星标项: string[] (带★▲等标记的关键条款，逐条列出)
- K11_废标条款: string[] (所有可能导致废标的条款，逐条列出)
- K12_章节模板要求: string (标书应包含的章节清单)
- K13_偏离表格式要求: string (格式/份数/装订等要求)
- K14_演示要求: string (是否需要演示、时长、形式)

如果某字段在文件中未找到，请填写"未找到"。仅返回 JSON，不要有其他文字。"""


def quick_extraction_messages(full_text: str) -> list[dict]:
    """快速模式：单次 LLM 调用提取 K01-K14。"""
    text_snippet = full_text[:15000]
    if len(full_text) > 15000:
        text_snippet += f"\n\n... [全文共 {len(full_text)} 字符，已截断]"

    return [
        {"role": "system", "content": QUICK_EXTRACTION_SYSTEM},
        {"role": "user", "content": f"招标文件内容：\n\n{text_snippet}"},
    ]


# ============================================================
# 辅助
# ============================================================

# Step 4 各模块描述 → 对应 BID_MODULE_DESCRIPTIONS
EXTRACTION_PROMPTS: dict[str, dict] = {
    module_key: {
        "name": info["description"],
        "fields": info["key_fields"],
    }
    for module_key, info in BID_MODULE_DESCRIPTIONS.items()
}


def system_prompt_for_step(step: str) -> str:
    """获取某步骤的系统 prompt。"""
    prompts = {
        "marker_semantics": MARKER_SEMANTICS_SYSTEM,
        "marker_extraction": MARKER_EXTRACTION_SYSTEM,
        "validation": VALIDATION_SYSTEM,
        "quick": QUICK_EXTRACTION_SYSTEM,
    }
    return prompts.get(step, ROLE_EXPERT)
