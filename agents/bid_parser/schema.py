"""
招标文件解析 — 完整数据模型

将 PDF 招标文件解析为目标结构化信息，下游驱动：
  1. 标书该写什么 → 从 templates + tech + qualification 生成写作大纲
  2. 标书写完校验 + 自打分 → 从 templates + rejection + scoring 生成检查清单

完整 JSON Schema 与 bid-parse skill 的 references/schema.json 对齐。
"""

# ============================================================
# 标记优先级
# ============================================================

MARKER_PRIORITY = {
    "FATAL": "显式废标标记 — 一旦出现，不满足必定废标",
    "CRITICAL": "关键标记 — 缺少对应内容则废标",
    "HIGH": "高优先级 — 严重扣分项",
    "MEDIUM": "中优先级 — 一般影响",
    "LOW": "低优先级 — 参考信息",
}

# ============================================================
# 默认标记符号
# ============================================================

DEFAULT_MARKERS = [
    "▲", "△",           # 核心技术要求 / 否决
    "★", "☆",           # 加分/优先项 / 星标
    "●", "○",           # 必须提交的材料
    "◇", "◆",           # 一般技术指标 / 强制资格
    "※",               # 特别注意
    "✓", "✔", "☑",     # 必须满足的准入条件
    "■", "□",           # 技术要求项
    "◎",               # 核心需求
    "①", "②", "③", "④", "⑤",  # 序号标记
    "⑴", "⑵", "⑶", "⑷", "⑸",
]

SYMBOL_ALIASES = {
    "▲": "核心技术要求/否决项",
    "△": "次要技术要求",
    "★": "加分项/星标条款",
    "☆": "优先项",
    "●": "必须提交",
    "○": "可选提交",
    "◇": "一般技术指标",
    "◆": "强制资格条件",
    "※": "特别注意",
    "✓": "必须满足",
    "✔": "必须满足",
    "☑": "准入条件",
    "■": "技术要求项",
    "□": "技术要求子项",
    "◎": "核心需求",
}

# ============================================================
# K01-K14 字段映射（从完整 schema → 旧格式兼容）
# ============================================================

K01_K14_MAPPING = {
    "K01_项目名称": {
        "source": "base.project_name",
        "description": "项目名称",
    },
    "K02_招标编号": {
        "source": "base.project_no",
        "description": "招标编号/项目编号",
    },
    "K03_招标人": {
        "source": "base.contact.name",
        "description": "招标人/采购人",
        "fallback": "base.binding_statements",
    },
    "K04_预算金额": {
        "source": "base.budget",
        "description": "预算金额/控制价",
        "format": lambda b: f"{b.get('amount', '')}{b.get('currency', '元')}" if isinstance(b, dict) else str(b),
    },
    "K05_投标截止时间": {
        "source": "base.bid_opening.deadline",
        "description": "投标截止时间",
    },
    "K06_开标时间": {
        "source": "logistics.bid_opening.time",
        "description": "开标时间",
        "fallback": "base.bid_opening.deadline",
    },
    "K07_评分标准": {
        "source": "scoring",
        "description": "评分标准概括",
        "format": "_format_scoring",
    },
    "K08_技术要求": {
        "source": "tech",
        "description": "技术要求概括",
        "format": "_format_tech",
    },
    "K09_商务资质要求": {
        "source": "qualification",
        "description": "商务资质要求",
        "format": "_format_qualification",
    },
    "K10_星标项": {
        "source": "marker_extractions.fatal_items",
        "description": "星标/关键条款",
        "format": "_format_marker_items",
    },
    "K11_废标条款": {
        "source": "rejection.conditions",
        "description": "废标/否决条款",
        "format": "_format_rejection",
    },
    "K12_章节模板要求": {
        "source": "templates",
        "description": "标书章节/模板要求",
        "format": "_format_templates",
    },
    "K13_偏离表格式要求": {
        "source": "templates.format_requirements",
        "description": "偏离表/格式要求",
        "format": "_format_deviation",
    },
    "K14_演示要求": {
        "source": "logistics.presentation_demo",
        "description": "演示/答辩要求",
        "format": "_format_presentation",
    },
}

# ============================================================
# 完整 BID_SCHEMA — 供 LLM structured output 参考
# ============================================================

# 以下为供 LLM 使用的简化版 schema 描述（仅关键字段）
# 完整 JSON Schema 见 references/schema.json（798行）
# 在 prompts 中会引用完整 schema 作为输出格式约束

BID_MODULE_DESCRIPTIONS = {
    "meta": {
        "description": "解析元数据：溯源信息、警告",
        "key_fields": ["parse_id", "source_file", "parse_time", "page_count", "warnings"],
    },
    "marker_semantics": {
        "description": "标记语义层：LLM 识别全文所有特殊标记符号的含义",
        "key_fields": ["total_marker_types_found", "markers[].symbol", "markers[].semantic_label", "markers[].priority", "markers[].maps_to_field"],
    },
    "marker_extractions": {
        "description": "标记内容精准抽取：正则定位 + LLM 分批映射到结构化字段",
        "key_fields": ["extraction_summary", "fatal_items", "critical_items", "high_items", "medium_items", "low_items"],
    },
    "base": {
        "description": "基本信息：项目名、编号、预算、保证金、投标方式等",
        "key_fields": ["project_name", "project_no", "bid_opening", "budget", "bid_security", "bid_validity_days", "bid_doc_mode"],
    },
    "qualification": {
        "description": "资格条件：逐条资质/业绩/人员/财务/信用要求 + 证明方式",
        "key_fields": ["requirements[].id", "requirements[].type", "requirements[].name", "requirements[].proof_type", "requirements[].is_mandatory"],
    },
    "rejection": {
        "description": "否决/废标条件：所有触发出局的规则 + 签章要求",
        "key_fields": ["conditions[].id", "conditions[].type", "conditions[].condition", "conditions[].severity", "sign_stamp_requirements"],
    },
    "scoring": {
        "description": "评分标准：维度权重 + 子项档位 + 加分项",
        "key_fields": ["method", "price_ratio", "tech_ratio", "commercial_ratio", "dimensions[].name", "dimensions[].max_score", "bonus_items"],
    },
    "tech": {
        "description": "技术需求：功能/非功能/安全/集成/交付/培训/运维",
        "key_fields": ["project_background", "functional_requirements", "non_functional_requirements", "security_requirements", "deliverables"],
    },
    "commercial": {
        "description": "商务需求：付款/质保/违约/履约保证金",
        "key_fields": ["payment", "delivery_cycle_days", "warranty", "penalty_clauses", "contract_type"],
    },
    "templates": {
        "description": "投标文件模板要求：章节清单 + 格式约束",
        "key_fields": ["bid_doc_structure[].section_no", "bid_doc_structure[].name", "format_requirements.copies", "format_requirements.electronic_format"],
    },
    "logistics": {
        "description": "投标操作要求：踏勘/答疑/递交/原件清单",
        "key_fields": ["bid_submission.method", "bid_submission.deadline", "bid_opening", "presentation_demo", "originals_to_bring"],
    },
}

# ============================================================
# K01-K14 字段 helper（新 shape：{value|items, source_page|source_pages}）
# ============================================================
#
# 旧 shape：标量是字符串、数组是 string[]
# 新 shape：{"value": "...", "source_page": 5}
#          {"items": [...], "source_pages": [12, 15]}
#
# 所有 helper 都兼容旧 shape（直接传字符串/数组也能用），
# 旧数据从 DB 读出来也不会炸。


def is_k_field_shaped(field) -> bool:
    """判断 K 字段是否已经是新 shape（dict 且带 value 或 items）。"""
    return isinstance(field, dict) and ("value" in field or "items" in field)


def k_field_value(field):
    """提取 K 字段的可显示值（标量返回 str，数组返回 list[str]）。

    空字符串/空数组/None 统一返回 None。
    """
    if isinstance(field, dict):
        if "value" in field:
            v = field["value"]
        elif "items" in field:
            v = field["items"]
        else:
            v = None
    else:
        v = field
    if v in (None, "", []):
        return None
    return v


def k_field_page(field) -> int | None:
    """提取 K 字段的来源页码。

    标量：取 source_page。数组：取 source_pages[0]（数组整体的大致首页）。
    无法确定时返回 None。
    """
    if not isinstance(field, dict):
        return None
    sp = field.get("source_page")
    if isinstance(sp, int) and sp > 0:
        return sp
    sps = field.get("source_pages")
    if isinstance(sps, list):
        for p in sps:
            if isinstance(p, int) and p > 0:
                return p
    return None


def k_field_items_with_pages(field) -> list[tuple[str, int | None]]:
    """提取数组型 K 字段的 (item, page) 列表。pages 缺失处用 None 占位。"""
    if isinstance(field, dict):
        items = field.get("items") or []
        pages = field.get("source_pages") or []
    elif isinstance(field, list):
        items = field
        pages = []
    else:
        return []
    out = []
    for i, item in enumerate(items):
        page = pages[i] if i < len(pages) else None
        if not isinstance(page, int) or page <= 0:
            page = None
        out.append((item, page))
    return out


def make_k_field(value, source_page: int | None = None):
    """构造新 shape 的 K 字段。数组用 source_pages，标量用 source_page。"""
    if isinstance(value, list):
        if source_page:
            return {"items": list(value), "source_pages": [source_page] * len(value)}
        return {"items": list(value), "source_pages": []}
    if source_page:
        return {"value": value, "source_page": source_page}
    return {"value": value, "source_page": None}


# ============================================================
# 辅助：K01-K14 格式化函数
# ============================================================

def _format_scoring(data) -> str:
    """将 scoring 模块格式化为 K07 文本。LLM 可能返回 dict 或 list。"""
    if not data or not isinstance(data, dict):
        return "未找到"
    method = data.get("method", "")
    price_r = data.get("price_ratio", 0)
    tech_r = data.get("tech_ratio", 0)
    comm_r = data.get("commercial_ratio", 0)
    dims = data.get("dimensions", [])
    dim_names = [d.get("name", "") for d in dims[:5] if isinstance(d, dict)]
    # 任意关键字段有值才视为有评分；否则未找到
    if not (method or price_r or tech_r or comm_r or dim_names):
        return "未找到"
    parts = []
    if method:
        parts.append(f"评标方法：{method}")
    if price_r or tech_r or comm_r:
        parts.append(f"价格{price_r}%+技术{tech_r}%+商务{comm_r}%")
    if dim_names:
        parts.append(f"维度：{'、'.join(dim_names)}")
    return "；".join(parts) if parts else "未找到"


def _format_tech(data) -> str:
    """将 tech 模块格式化为 K08 文本。LLM 可能返回 dict 或 list。"""
    if not data or not isinstance(data, dict):
        return "未找到"
    bg = data.get("project_background", {})
    func_reqs = data.get("functional_requirements", [])
    if not isinstance(func_reqs, list):
        func_reqs = []
    modules = list({r.get("module", "") for r in func_reqs if isinstance(r, dict) and r.get("module")})
    parts = []
    if isinstance(bg, dict) and bg.get("summary"):
        parts.append(bg["summary"][:100])
    if modules:
        parts.append(f"覆盖模块：{'、'.join(modules[:8])}")
    return "；".join(parts) if parts else "未找到"


def _format_qualification(data) -> str:
    """将 qualification 模块格式化为 K09 文本。LLM 可能返回 dict 或 list。"""
    if not data:
        return "未找到"
    # LLM 可能直接返回 list（[{name, proof_type, ...}, ...]）
    if isinstance(data, list):
        reqs = data
    elif isinstance(data, dict):
        reqs = data.get("requirements", [])
    else:
        return "未找到"
    items = []
    for r in reqs[:10]:
        if not isinstance(r, dict):
            items.append(str(r))
            continue
        name = r.get("name", "") or r.get("requirement", "") or r.get("text", "")
        ptype = r.get("proof_type", "")
        items.append(f"{name}({ptype})" if ptype and name else (name or "未找到"))
    return "；".join(items) if items else "未找到"


def _format_marker_items(data) -> list:
    """提取 FATAL+CRITICAL 标记文本为 K10 列表。LLM 可能返回 list 或 dict。"""
    if not data or not isinstance(data, list):
        return []
    items = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = item.get("raw_text", "") or item.get("semantic", "")
        if text:
            marker = item.get("marker", "")
            items.append(f"{marker} {text}" if marker else text)
    return items[:20]


def _format_rejection(data) -> list:
    """提取废标条件为 K11 列表。LLM 可能返回 list 或 dict。"""
    if not data or not isinstance(data, list):
        return []
    return [c.get("condition", "") for c in data if isinstance(c, dict) and c.get("condition")][:20]


def _format_templates(data) -> str:
    """将 templates 模块格式化为 K12 文本。LLM 可能返回 dict 或 list。"""
    if not data or not isinstance(data, dict):
        return "未找到"
    structure = data.get("bid_doc_structure", [])
    if structure and isinstance(structure, list):
        chapters = [f"{s.get('section_no', '')} {s.get('name', '')}" for s in structure[:10] if isinstance(s, dict)]
        return f"共{len(structure)}章：" + "、".join(chapters)
    return "未找到"


def _format_deviation(data) -> str:
    """将 format_requirements 格式化为 K13 文本。LLM 可能返回 dict 或 list。"""
    if not data or not isinstance(data, dict):
        return "未找到"
    copies = data.get("copies", {}) or {}
    parts = []
    if copies and isinstance(copies, dict):
        parts.append(f"正本{copies.get('original', '?')}份/副本{copies.get('copy', '?')}份")
    if data.get("electronic_format"):
        parts.append(f"电子版：{data['electronic_format']}")
    if data.get("binding_method"):
        parts.append(f"装订：{data['binding_method']}")
    return "；".join(parts) if parts else "未找到"


def _format_presentation(data: dict) -> str:
    """将 presentation_demo 格式化为 K14 文本"""
    if not data:
        return "未找到"
    if isinstance(data, dict):
        required = "需要" if data.get("required") else "不需要"
        duration = data.get("duration_min", "")
        fmt = data.get("format", "")
        parts = [f"演示：{required}"]
        if duration:
            parts.append(f"{duration}分钟")
        if fmt:
            parts.append(f"格式：{fmt}")
        return "；".join(parts)
    return str(data)


# 注册格式化函数
K01_K14_FORMATTERS = {
    "K04_预算金额": _format_scoring.__doc__ and None,  # 被 lambda 覆盖
    "K07_评分标准": _format_scoring,
    "K08_技术要求": _format_tech,
    "K09_商务资质要求": _format_qualification,
    "K10_星标项": _format_marker_items,
    "K11_废标条款": _format_rejection,
    "K12_章节模板要求": _format_templates,
    "K13_偏离表格式要求": _format_deviation,
    "K14_演示要求": _format_presentation,
}
