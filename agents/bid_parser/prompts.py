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
        "full_parse": FULL_PARSE_SYSTEM,
    }
    return prompts.get(step, ROLE_EXPERT)


# ============================================================
# 阶段 1：单次全量解析（1M 上下文单调用）— 替代旧的五步管道
# ============================================================

FULL_PARSE_SYSTEM = """你是招标文件解析专家。给定完整招标文件文本，一次性提取所有结构化信息。

## 输出 JSON Schema

{
  // ── K01-K14 用户友好层（精炼字符串/数组，给 UI 展示用）──
  "K01_项目名称": "string, 项目全称，未找到填'未找到'",
  "K02_招标编号": "string, 招标/项目编号",
  "K03_招标人": "string, 招标人/采购人名称",
  "K04_预算金额": "string, 含单位如'165万元'，未找到填'未找到'",
  "K05_投标截止时间": "string, ISO 8601 或原文表述",
  "K06_开标时间": "string, ISO 8601 或原文表述",
  "K07_评分标准": "string, 简述评标方法与权重（例：综合评分法 价格30% 技术50% 商务20%）",
  "K08_技术要求": "string, 简述主要技术需求（模块/性能/集成）",
  "K09_商务资质要求": "string, 列出关键资质/业绩/人员/财务要求",
  "K10_星标项": ["string", ...],  // 带★/▲等关键标记的条款，逐条列出
  "K11_废标条款": ["string", ...],  // 所有可能导致废标的条款，逐条列出
  "K12_章节模板要求": "string, 投标文件应包含的章节清单",
  "K13_偏离表格式要求": "string, 描述正本/副本/电子版/装订要求",
  "K14_演示要求": "string, 是否需要演示、时长、形式",

  // ── 8 个结构化模块（机器可读，下游 Agent 使用）──
  "base": {
    "project_name": "string",
    "project_no": "string",
    "bid_opening": {
      "deadline": "string, 投标截止时间 ISO 8601",
      "open_time": "string, 开标时间 ISO 8601"
    },
    "budget": {
      "amount": <number, 单位元, 例 1650000>,
      "currency": "CNY"
    },
    "bid_security": <number, 投标保证金金额, 单位元>,
    "bid_validity_days": <number, 投标有效期天数>,
    "bid_doc_mode": "string, 单轨制/双轨制/电子招投标"
  },

  "qualification": {
    "requirements": [
      {
        "id": "Q01",
        "name": "string, 资质/业绩/人员/财务/信用条款名",
        "type": "公司资质|业绩案例|人员要求|财务要求|信用要求|其他",
        "proof_type": "string, 证明方式（证书/合同/报表/承诺函等）",
        "is_mandatory": <bool>
      }
    ]
  },

  "rejection": {
    "conditions": [
      {
        "id": "R01",
        "type": "废标|否决|无效投标|资格不符",
        "condition": "string, 完整描述",
        "severity": "FATAL|HIGH|MEDIUM",
        "source_marker": "string, 触发该条款的原文标记符号如★/▲，无则为空"
      }
    ],
    "sign_stamp_requirements": "string, 签章/盖章/签字要求"
  },

  "scoring": {
    "method": "string, 综合评分法|最低评标价法|性价比法|其他",
    "price_ratio": <number 0-100, 价格权重>,
    "tech_ratio": <number 0-100, 技术权重>,
    "commercial_ratio": <number 0-100, 商务权重>,
    "dimensions": [
      {
        "name": "string, 评分维度如'技术方案'",
        "max_score": <number, 该维度最高分>,
        "sub_items": [
          {"name": "string, 子项名", "score": <number, 最高分>, "criteria": "string, 评分标准"}
        ]
      }
    ],
    "bonus_items": [
      {"name": "string, 加分项名", "max_score": <number, 最高加分>}
    ]
  },

  "tech": {
    "project_background": {
      "summary": "string, 项目背景简述"
    },
    "functional_requirements": [
      {
        "module": "string, 所属系统模块如'用户管理'",
        "name": "string, 需求名",
        "description": "string, 详细描述",
        "priority": "FATAL|HIGH|MEDIUM|LOW"
      }
    ],
    "non_functional_requirements": {
      "performance": "string, 性能要求（并发/TPS/响应时间）",
      "availability": "string, 可用性要求",
      "scalability": "string, 扩展性要求"
    },
    "security_requirements": {
      "level": "string, 等保级别",
      "items": ["string, 安全要求条目"]
    },
    "deliverables": ["string, 交付物清单"]
  },

  "commercial": {
    "payment": "string, 付款方式/分期",
    "delivery_cycle_days": <number, 交付周期天数>,
    "warranty": "string, 质保期/维保期",
    "penalty_clauses": "string, 违约责任",
    "contract_type": "string, 合同类型"
  },

  "templates": {
    "bid_doc_structure": [
      {
        "section_no": "string, 章节号如'第六章'",
        "name": "string, 章节名",
        "required": <bool>,
        "pages_min": <number, 最少页数, 可选>
      }
    ],
    "format_requirements": {
      "copies": {"original": <number, 正本份数>, "copy": <number, 副本份数>},
      "electronic_format": "string, 电子版格式（PDF/Word/加密zip）",
      "binding_method": "string, 装订方式"
    }
  },

  "logistics": {
    "bid_submission": {
      "method": "string, 现场递交|线上提交|邮寄",
      "deadline": "string, 截止时间 ISO 8601",
      "address": "string, 递交地址"
    },
    "bid_opening": {
      "time": "string, 开标时间 ISO 8601",
      "location": "string, 开标地点",
      "live": <bool, 是否直播>
    },
    "presentation_demo": {
      "required": <bool>,
      "duration_min": <number, 时长分钟>,
      "format": "string, 形式（现场/视频/PPT）"
    },
    "originals_to_bring": ["string, 现场需携带的原件清单"]
  },

  "marker_extractions": {
    "extraction_summary": {
      "total_marker_occurrences": <int, 全文标记符号总出现次数>,
      "total_mapped": <int, 已映射到结构化字段的条数>,
      "unmapped_count": <int, 未映射条数, 一般填 0>
    },
    "fatal_items": [
      {
        "marker": "string, 符号如★",
        "source_page": <int, 来源页码>,
        "raw_text": "string, 原文（完整保留, 不省略）",
        "semantic": "string, 语义解释"
      }
    ],
    "critical_items": [...],   // 结构同 fatal_items
    "high_items": [...],
    "medium_items": [...],
    "low_items": [...]
  }
}

## 关键原则

1. **K 层是给用户看的精炼版**（字符串/数组），模块层是机器可读的结构化数据。两者信息一致但表达粒度不同。
2. **数字字段必须是 JSON number**，不要带"元"/"万元"等单位。例：`budget.amount = 1650000`，不是 "165万"。
3. **找不到信息时**：K 字段填"未找到"，模块字段填 null 或空数组/空对象。
4. **绝不编造**：原文中没有的信息不要补全。如果只有部分信息能确定，其他字段填 null。
5. **标记抽取尽量穷尽**：原文中每个 ★/▲/●/◆ 等符号对应的条款都要在 marker_extractions 对应优先级数组里出现。
6. **跨章推理**：K04 字符串与 base.budget.amount 应该一致；K05 与 logistics.bid_submission.deadline 应该一致。
7. **输出必须是合法 JSON**，放在 ```json 代码块中或直接输出。
"""


def full_parse_messages(full_text: str) -> list[dict]:
    """
    阶段 1：单次全量解析 prompt。
    System prompt 定义完整 JSON schema；user prompt 是文档全文。

    依赖：DeepSeek V3.1+/V4 1M 上下文，79 页文档约 25K tokens，
    加上 system 约 27K tokens，远在 1M 上下文的承受范围。

    Returns:
        OpenAI 格式 messages 列表
    """
    return [
        {"role": "system", "content": FULL_PARSE_SYSTEM},
        {"role": "user", "content": (
            f"以下是完整招标文件（共 {len(full_text)} 字符）。\n"
            f"请按 system prompt 的 schema 一次性输出全部 JSON。\n\n"
            f"---\n\n{full_text}"
        )},
    ]
