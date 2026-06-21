"""
MatcherAgent — 标书提纲设计 + 材料匹配（v3 重构）

两阶段：
  1. generate_outline(ctx) — 基于 K01/K08/K10/K12 + K 模板要求，LLM 生成 2 级章节大纲
  2. match_materials(ctx) — 用确认后的提纲做直接分类匹配，输出章节-材料映射

**材料库假设**（决策记录）：
  匹配逻辑依赖材料 `category` 和 `title` 字段已按投标文件常用分类预组织。
  材料直接从 `materials/` 文件夹读取（不走数据库），文件名即标题，目录即分类：
    01_公司资质, 02_业绩案例, 03_技术方案, 04_实施方案, 05_商务文件, 06_其他
  不做语义相似度搜索（TF-IDF/embedding）—— 那会导致"过度重叠"匹配到不相关材料。
  **直接把材料放到正确的分类**比任何智能匹配都更准。

  本方法做的是 3 层 fallback：
    1) Material.category == chapter["category"]      → match_score: "高"
    2) chapter 关键词在 Material.title 里命中         → match_score: "中"
    3) 都为空                                         → match_score: "低" / "需新建"
"""
import json
import logging
import re
from pathlib import Path
from typing import Any

from agents.base import BaseAgent, AgentContext
from agents.bid_parser.evidence import evidence_from_k_field, make_evidence_ref
from agents.bid_parser.pipeline import BidLLMClient
from agents.bid_parser.schema import k_field_value, k_field_items_with_pages

logger = logging.getLogger(__name__)

# 6 个标准分类——LLM 生成提纲时优先对齐
STANDARD_CATEGORIES = [
    "01_公司资质",
    "02_业绩案例",
    "03_技术方案",
    "04_实施方案",
    "05_商务文件",
    "06_其他",
]

STANDARD_VOLUMES = ["commercial", "technical", "price", "other"]

OUTLINE_SYSTEM_PROMPT = """你是医院信息化投标文件的标书结构规划师。**每个项目的标书结构都不同**，
由招标文件的实际要求决定，不是套用固定模板。

任务：根据下方提供的 K01–K14 招标文件解析数据 + `scoring_breakdown` 详细评分项列表，
设计一份 2 级章节大纲。

`scoring_breakdown` 是关键输入：每个评分维度（dimension）下的子项（sub_item）都带独立
分值，这是评审专家分别打分的对象。K07 字符串常被截断，必须读 `scoring_breakdown` 拿完整
评分项列表。

**设计原则**（重要）：

1) **K07 评分标准是结构骨架的核心**。
   - 输入包含 `scoring_breakdown`（带独立分值的子项列表），**优先从这里读取完整评分项**。
   - 不要只看大项（如"技术30% 商务20%"），要**逐条读每个得分点的详细描述**。
   - 例：评分项写"系统架构设计（5分）、数据库设计（3分）、接口设计（2分）"，
     "系统架构设计"、"数据库设计"、"接口设计"应直接成为对应章节的小节。
   - 评分占比高 = 章节重要，评分占比低 / 没评分 = 章节可简化。
   - 商务、价格、服务的评分项同理，分别映射到对应章节的小节。
   - **`scoring_breakdown` 中带独立分值的子项（如"售后服务与运维方案3%"、"需求方案3%"、
     "实施方案3%"）应各自成为独立的一级章节**。这些是评审专家分别打分的对象，
     不能合并塞到其他章节下做小节——那样评审时找不到对应内容，丢分。

2) **K12 章节模板要求**：
   - 如果 K12 是一组**文件/部分混杂列表**（如"投标文件应包括：资格审查索引表、
     评审索引表、投标函、开标一览表..."），**不要平铺成 8 个独立的一级章节**。
     把同类项归到 6 大分类章节下做小节：
       - 资格审查/评审索引/投标函/开标一览表/分项报价表/商务偏离表/政府采购政策/
         信用承诺书 → 05_商务文件 章节下做小节
       - 供应商基本情况表/资格证明文件/资质证书 → 01_公司资质 章节下做小节
       - 类似项目业绩 → 02_业绩案例 章节
       - 技术条款偏离表 → 03_技术方案 章节下做小节
   - 如果 K12 是**结构化目录**（"第一章 xxx 第二章 xxx ..." 明确给出 N 个一级章节），
     **严格按其顺序和标题**，不要重新组织。
   - 如果是空话（"按招标文件要求"、"详见附件"），根据 K07/K08/K09/K11 设计。
   - **K12 已列出的内容不要重复成独立章节**（如 K12 已含"商务条款偏离表"，
     就不要再单独造一个"商务文件"章节）。

3) **K13 偏离表格式要求**：
   - 明确要求商务/技术偏离表的 → 05_商务文件 加"商务偏离表"小节，
     03_技术方案 加"技术偏离表"小节。
   - 没要求 → 不加。

4) **K14 演示要求**：
   - 要求演示 / PPT / 视频讲解的 → 03_技术方案 或 04_实施方案 加"演示方案" /
     "系统演示"小节，并按演示内容设计对应小节。
   - 没要求 → 不加。

5) **K11 废标条款**：
   - 提到的合规要点 → 05_商务文件 加"废标条款响应"或"合规性声明"小节。
   - 没要求 → 不加。

6) **K09 商务资质要求**：
   - 列了具体证书名（ISO9001、信息安全等）的 → 01_公司资质 为每个证书单独小节。
   - 没列 → 通用"资质证书"小节。

7) **章节不必都有**：演示、应急预案、培训方案等**根据招标文件实际要求决定**。
   招标方没要求的章节不要加（精准对标，不堆砌）。

8) **2 级深度**：一级章节 5-10 个；K07 评分项多时一章可达 6-8 个小节，
   否则 2-4 个。

9) **优先对齐 6 个标准分类**（用于材料库匹配）：
   01_公司资质 / 02_业绩案例 / 03_技术方案 / 04_实施方案 / 05_商务文件 / 06_其他
   每个一级章节 `category` 必须是其中之一。
   - 业绩、案例、过往项目 → 02_业绩案例（**不要归到 06_其他**）
   - 售后服务与运维方案 → 03_技术方案（K07 独立评分项时成独立一级章节）
   - 演示方案 → 03_技术方案 或 04_实施方案 下的小节（不要单独成章节）

10) **不编造具体业务细节**（如项目名、金额、证书编号），只列章节标题。

**严格返回 JSON**，格式：
{
  "outline": [
    {
      "id": "ch1",
      "no": 1,
      "title": "公司资质",
      "volume": "commercial",
      "category": "01_公司资质",
      "subsections": [
        {"id": "ch1.1", "title": "营业执照与法人证明"}
      ],
      "source": "k12" | "scoring" | "llm_inferred"
    }
  ]
}

`volume` 取值：
- `commercial`：商务标/资格/业绩/商务文件
- `technical`：技术标/技术方案/实施方案/售后运维
- `price`：报价标/价格文件/开标一览表/分项报价
- `other`：无法归类但仍需保留的内容

`source` 取值：
- `k12`：来自 K12 模板要求
- `scoring`：来自 K07 评分项映射
- `llm_inferred`：根据 K08/K09/K11/K13/K14 推断

只返回 JSON，不要任何解释文字。"""


class MatcherAgent(BaseAgent):
    name = "matcher"
    description = "将招标文件章节要求与材料库进行智能匹配"
    system_prompt = OUTLINE_SYSTEM_PROMPT
    temperature = 0.1

    # ================================================================
    # 一次性入口（自动工作流 + Web SSE 走这里）
    # ================================================================

    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        """一次性：生成提纲 + 匹配材料。供 run_workflow 和 Web 一键式调用。"""
        outline = self.generate_outline(ctx)
        match = self.match_materials(ctx)
        return {
            "outline": outline.get("outline", []),
            "chapters": match.get("chapters", []),
            "total": match.get("total", 0),
        }

    # ================================================================
    # 阶段 1：提纲设计
    # ================================================================

    def generate_outline(self, ctx: AgentContext,
                         hint: str | None = None) -> dict[str, Any]:
        """基于 K01-K14 全字段，由 LLM 设计 2 级章节大纲。

        关键设计：
        - 把所有 K 字段（不只 K01/K08/K10/K12）完整喂给 LLM
        - 不预解析 K07/K12 → 让 LLM 自己读、自己判断
        - LLM 看 K13/K14/K11 决定要不要加偏离表/演示/合规章节
        降级路径：LLM 失败 → bid_doc_structure → 6 大分类骨架。
        """
        parsed = ctx.parsed_data or {}
        bid_doc_structure = (
            (parsed.get("templates") or {}).get("bid_doc_structure") or []
        )

        # 收集 K01–K14 完整内容（不截断）
        tender_data = {
            "K01_项目名称": k_field_value(parsed.get("K01_项目名称")),
            "K02_招标编号": k_field_value(parsed.get("K02_招标编号")),
            "K03_招标人": k_field_value(parsed.get("K03_招标人")),
            "K04_预算金额": k_field_value(parsed.get("K04_预算金额")),
            "K05_投标截止时间": k_field_value(parsed.get("K05_投标截止时间")),
            "K06_开标时间": k_field_value(parsed.get("K06_开标时间")),
            "K07_评分标准": k_field_value(parsed.get("K07_评分标准")),
            "K08_技术要求": k_field_value(parsed.get("K08_技术要求")),
            "K09_商务资质要求": k_field_value(parsed.get("K09_商务资质要求")),
            "K10_星标项": [
                item for item, _page in
                k_field_items_with_pages(parsed.get("K10_星标项"))
            ][:20],
            "K11_废标条款": k_field_value(parsed.get("K11_废标条款")),
            "K12_章节模板要求": k_field_value(parsed.get("K12_章节模板要求")),
            "K13_偏离表格式要求": k_field_value(parsed.get("K13_偏离表格式要求")),
            "K14_演示要求": k_field_value(parsed.get("K14_演示要求")),
        }
        # 去掉 None 值（让 LLM 看到的 input 更紧凑）
        tender_data = {k: v for k, v in tender_data.items() if v}

        # 详细评分结构（K07 字符串常被截断丢失子项，scoring.dimensions 是完整数据）
        scoring = parsed.get("scoring") or {}
        scoring_flat: list[dict[str, Any]] = []
        for dim in scoring.get("dimensions") or []:
            for sub in dim.get("sub_items") or []:
                scoring_flat.append({
                    "dimension": dim.get("name"),
                    "max_score": dim.get("max_score"),
                    "sub_item": sub.get("name"),
                    "score": sub.get("score"),
                    "criteria": sub.get("criteria"),
                })
        bonus = [
            {"name": b.get("name"), "max_score": b.get("max_score")}
            for b in scoring.get("bonus_items") or []
        ]

        user_payload: dict[str, Any] = {
            "tender_data": tender_data,
            "preset_outline": bid_doc_structure,
            "standard_categories": STANDARD_CATEGORIES,
            "scoring_breakdown": scoring_flat,
            "scoring_bonus": bonus,
        }
        if hint:
            user_payload["user_hint"] = hint

        messages = [
            {"role": "system", "content": OUTLINE_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

        client = BidLLMClient()
        outline_chapters: list[dict[str, Any]] = []
        used_fallback = False

        if client.is_available:
            try:
                data = client.chat_json(messages, temperature=0.1, max_tokens=4096)
                if data:
                    outline_chapters = self._normalize_outline(
                        data.get("outline") or []
                    )
            except Exception as e:
                logger.warning("LLM 提纲生成失败，使用降级路径: %s", e)

        if not outline_chapters:
            outline_chapters = self._fallback_outline(bid_doc_structure)
            used_fallback = True

        outline_chapters = self._attach_outline_refs(outline_chapters, parsed)

        # 写回 ctx
        ctx.outline = outline_chapters
        ctx.parsed_data["_generated_outline"] = outline_chapters
        ctx.parsed_data["_outline_source"] = (
            "fallback" if used_fallback else "llm"
        )
        ctx.error = None

        # 静态验证（Phase 0 - Task 0.1）
        validation = validate_outline(
            outline=outline_chapters,
            scoring=scoring,
            k12=k_field_value(parsed.get("K12_章节模板要求")),
        )

        return {
            "outline": outline_chapters,
            "total": len(outline_chapters),
            "version": "1.0",
            "source": "fallback" if used_fallback else "llm",
            "validation": validation,  # 新增验证结果
        }

    # ================================================================
    # 阶段 2：材料匹配
    # ================================================================

    def match_materials(self, ctx: AgentContext) -> dict[str, Any]:
        """用 ctx.outline（已确认）做直接分类匹配。降级：没有 outline → 报错。"""
        outline = ctx.outline
        if not outline:
            ctx.error = "没有可用的提纲，请先生成并确认提纲"
            return {"chapters": [], "total": 0, "error": ctx.error}

        # 从文件系统加载材料库（不走数据库）
        material_dicts = self._load_materials_from_disk()

        chapters: list[dict[str, Any]] = []
        for ch in outline:
            matches = self._match_chapter_to_materials(ch, material_dicts)
            primary = matches[0] if matches else {
                "file_path": None,
                "material_title": "无匹配材料",
                "match_score": "低",
                "reason": "需新建",
            }
            chapters.append({
                "chapter": ch.get("title", ""),
                "chapter_id": ch.get("id", ""),
                "volume": ch.get("volume", "other"),
                "category": ch.get("category", ""),
                "file_path": primary["file_path"],
                "material_title": primary["material_title"],
                "match_score": primary["match_score"],
                "reason": primary["reason"],
                "alternatives": matches[1:] if len(matches) > 1 else [],
            })

        ctx.chapters = chapters
        ctx.error = None
        return {"chapters": chapters, "total": len(chapters)}

    # ================================================================
    # 辅助：从文件系统加载材料库
    # ================================================================

    def _load_materials_from_disk(self) -> list[dict[str, Any]]:
        """从 materials/ 文件夹加载材料，不走数据库。

        Returns:
            [{
                "file_path": str,
                "title": str,       # 文件名（去扩展名）
                "category": str,    # 父目录名
                "tags": str,        # 空（未来可从文件 frontmatter 读）
            }]
        """
        materials_dir = Path(__file__).parent.parent / "materials"
        if not materials_dir.exists():
            logger.warning(f"材料库目录不存在: {materials_dir}")
            return []

        result: list[dict[str, Any]] = []
        for cat_dir in materials_dir.iterdir():
            if not cat_dir.is_dir() or cat_dir.name.startswith("."):
                continue
            category = cat_dir.name
            if category not in STANDARD_CATEGORIES:
                continue

            for file_path in cat_dir.iterdir():
                if file_path.name in (".gitkeep", ".DS_Store") or file_path.is_dir():
                    continue
                # MVP 只支持 .md 和 .docx
                if file_path.suffix.lower() not in (".md", ".docx"):
                    continue

                title = file_path.stem  # 文件名（去扩展名）
                result.append({
                    "file_path": str(file_path),
                    "title": title,
                    "category": category,
                    "tags": "",
                })

        logger.info(f"从 {materials_dir} 加载 {len(result)} 个材料")
        return result

    # ================================================================
    # 辅助：单章节 → 材料列表
    # ================================================================

    def _match_chapter_to_materials(
        self, chapter: dict[str, Any], materials: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """3 层 fallback：分类精确 → 标题关键词 → 空。"""
        target_category = chapter.get("category", "")

        # Tier 1: 精确分类匹配
        tier1 = [m for m in materials if m["category"] == target_category]
        if tier1:
            # 优先级排序：标题完全匹配 > 标题子串匹配 > 其他同分类材料
            chapter_title = chapter.get("title", "").strip()
            # 去掉章节编号前缀
            title_cleaned = re.sub(r"^第[一二三四五六七八九十\d]+[章节部分][\s\:：、]?", "", chapter_title)
            title_cleaned = re.sub(r"^\d+[\.\s\:：、]+", "", title_cleaned).strip()

            # 评分排序
            scored = []
            for m in tier1:
                mtitle = m["title"]
                score = 0
                # 完全匹配（如"技术方案" == "项目技术方案"的核心部分）
                if title_cleaned and title_cleaned in mtitle:
                    score = 100
                # 反向匹配（文件名在章节标题中）
                elif mtitle and mtitle in title_cleaned:
                    score = 90
                # 同分类但标题无关
                else:
                    score = 50
                scored.append((m, score))

            # 按分数降序
            scored.sort(key=lambda x: x[1], reverse=True)

            return [{
                "file_path": m["file_path"],
                "material_title": m["title"],
                "match_score": "高",
                "reason": f"标准分类「{target_category}」直接匹配",
            } for m, _ in scored[:3]]

        # Tier 2: 章节标题直接在文件名中出现（子串匹配）
        title = chapter.get("title", "").strip()
        if title:
            # 去掉章节编号前缀（如"第N章"、"1."等）
            title_cleaned = re.sub(r"^第[一二三四五六七八九十\d]+[章节部分][\s\:：、]?", "", title)
            title_cleaned = re.sub(r"^\d+[\.\s\:：、]+", "", title_cleaned).strip()

            tier2: list[tuple[dict[str, Any], str]] = []
            for m in materials:
                mtitle = m["title"] or ""
                # 章节标题直接出现在文件名中（至少 3 个字）
                if len(title_cleaned) >= 3 and title_cleaned in mtitle:
                    tier2.append((m, title_cleaned))
                # 或者文件名直接出现在章节标题中（反向匹配，处理"售后服务方案"匹配"售后服务"）
                elif len(mtitle) >= 3 and mtitle in title_cleaned:
                    tier2.append((m, mtitle))

            if tier2:
                return [{
                    "file_path": m["file_path"],
                    "material_title": m["title"],
                    "match_score": "中",
                    "reason": f"标题匹配「{hit}」",
                } for m, hit in tier2[:3]]

        # Tier 3: 无匹配
        return [{
            "file_path": None,
            "material_title": "无匹配材料",
            "match_score": "低",
            "reason": "需新建",
        }]

    @staticmethod
    def _extract_chapter_keywords(title: str) -> list[str]:
        """从章节标题里提关键词：去前缀 → 全标题 + 2/3/4 字中文滑动窗口。

        例："临床试验数字化方案" → ["临床试验数字化方案",
                                    "临床", "床试", "试验", "验数", "数字", "字化", "化方", "方案",
                                    "临床试", "床试验", "试验数", "验数字", "数字化", "字化方", "化方案",
                                    "临床试验", "床试验数", "试验数字", "验数字化", "数字化方", "字化方案"]

        这样 tier-2 匹配能容忍材料标题里多/少几个字。
        """
        if not title:
            return []
        # 去掉「第N章」「第N节」「1.」「（一）」等前缀
        cleaned = re.sub(
            r"^第[一二三四五六七八九十\d]+\s*[章节部分条款][\s\:：、]?",
            "", title,
        )
        cleaned = re.sub(r"^\d+[\.\s\:：、]+", "", cleaned)
        cleaned = cleaned.strip()
        if not cleaned:
            return []

        out: list[str] = []
        seen: set[str] = set()
        # 1) 全标题优先
        if cleaned not in seen:
            out.append(cleaned)
            seen.add(cleaned)
        # 2) 2/3/4 字中文滑动窗口
        for size in (2, 3, 4):
            for i in range(len(cleaned) - size + 1):
                w = cleaned[i:i + size]
                # 必须是纯中文（避免英文/数字窗口污染）
                if re.match(r"^[一-鿿]+$", w) and w not in seen:
                    out.append(w)
                    seen.add(w)
        return out

    # ================================================================
    # 辅助：提纲归一化 / 降级
    # ================================================================

    @staticmethod
    def _normalize_outline(raw: list[Any]) -> list[dict[str, Any]]:
        """LLM 输出 → 标准 outline schema。"""
        out: list[dict[str, Any]] = []
        for i, ch in enumerate(raw, 1):
            if not isinstance(ch, dict):
                continue
            title = str(ch.get("title") or "").strip()
            if not title:
                continue
            cid = ch.get("id") or f"ch{i}"
            category = ch.get("category") or ""
            if category not in STANDARD_CATEGORIES:
                category = "06_其他"
            volume = ch.get("volume") or ""
            if volume not in STANDARD_VOLUMES:
                volume = MatcherAgent._infer_volume(
                    title=title,
                    category=category,
                )
            subs_raw = ch.get("subsections") or []
            subs: list[dict[str, Any]] = []
            for j, s in enumerate(subs_raw, 1):
                if isinstance(s, dict):
                    st = str(s.get("title") or "").strip()
                else:
                    st = str(s).strip()
                if not st:
                    continue
                # 去重：跳过与父章节标题相同/包含关系的小节（LLM 偶尔重复）
                if st == title or st in title or title in st:
                    continue
                subs.append({
                    "id": s.get("id") if isinstance(s, dict) and s.get("id") else f"{cid}.{j}",
                    "title": st,
                })
            # 重新编号：1, 2, 3...（LLM 偶尔跳过数字，如 ch3.1, ch3.3, ch3.4）
            for k, s in enumerate(subs, 1):
                s["id"] = f"{cid}.{k}"
            out.append({
                "id": cid,
                "no": i,
                "title": title,
                "volume": volume,
                "category": category,
                "subsections": subs,
                "source": ch.get("source") or "llm_inferred",
            })
        return out

    @staticmethod
    def _fallback_outline(
        bid_doc_structure: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """无 LLM 时构造提纲：优先用解析里的 bid_doc_structure，其次 6 大分类骨架。"""
        if bid_doc_structure:
            out = []
            for i, item in enumerate(bid_doc_structure, 1):
                name = item.get("name") or item.get("section_no") or f"第{i}章"
                cid = f"ch{i}"
                # 简单映射分类
                category = "06_其他"
                for cat in STANDARD_CATEGORIES:
                    if any(
                        kw in name
                        for kw in ["资质", "公司", "营业执照", "法人"]
                    ) and cat == "01_公司资质":
                        category = cat
                        break
                    if any(
                        kw in name
                        for kw in ["业绩", "案例", "历史", "项目经验"]
                    ) and cat == "02_业绩案例":
                        category = cat
                        break
                    if any(
                        kw in name
                        for kw in ["技术", "方案", "架构", "系统设计"]
                    ) and cat == "03_技术方案":
                        category = cat
                        break
                    if any(
                        kw in name
                        for kw in ["实施", "部署", "培训", "运维"]
                    ) and cat == "04_实施方案":
                        category = cat
                        break
                    if any(
                        kw in name
                        for kw in ["商务", "报价", "合同", "付款"]
                    ) and cat == "05_商务文件":
                        category = cat
                        break
                out.append({
                    "id": cid,
                    "no": i,
                    "title": name,
                    "volume": MatcherAgent._infer_volume(
                        title=name,
                        category=category,
                    ),
                    "category": category,
                    "subsections": [],
                    "source": "fallback",
                })
            return out

        # 最后兜底：6 大分类骨架
        return [
            {"id": f"ch{i+1}", "no": i + 1, "title": cat.split("_", 1)[1],
             "volume": MatcherAgent._infer_volume(title=cat, category=cat),
             "category": cat, "subsections": [], "source": "fallback"}
            for i, cat in enumerate(STANDARD_CATEGORIES)
        ]

    @staticmethod
    def _infer_volume(title: str, category: str) -> str:
        """Infer bid volume from chapter title and material category."""
        text = f"{title or ''} {category or ''}"
        if any(kw in text for kw in ["报价", "价格", "开标一览", "分项报价", "投标报价"]):
            return "price"
        if category in ("03_技术方案", "04_实施方案"):
            return "technical"
        if category in ("01_公司资质", "02_业绩案例", "05_商务文件"):
            return "commercial"
        if any(kw in text for kw in ["技术", "实施", "运维", "售后", "培训", "演示"]):
            return "technical"
        if any(kw in text for kw in ["商务", "资质", "业绩", "投标函", "承诺", "合同"]):
            return "commercial"
        return "other"

    @staticmethod
    def _attach_outline_refs(
        outline: list[dict[str, Any]],
        parsed: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Attach best-effort requirement/scoring evidence refs to outline rows."""
        k12_refs = evidence_from_k_field(
            parsed.get("K12_章节模板要求"),
            "K12_章节模板要求",
        )
        scoring_refs = evidence_from_k_field(
            parsed.get("K07_评分标准"),
            "K07_评分标准",
        )
        scoring = parsed.get("scoring") or {}
        detailed_scoring_refs: list[dict[str, Any]] = []
        for dim_i, dim in enumerate(scoring.get("dimensions") or []):
            if not isinstance(dim, dict):
                continue
            dim_name = dim.get("name") or ""
            for sub_i, sub in enumerate(dim.get("sub_items") or []):
                if not isinstance(sub, dict):
                    continue
                quote = "；".join(
                    str(v) for v in [
                        dim_name,
                        sub.get("name"),
                        sub.get("score"),
                        sub.get("criteria"),
                    ] if v not in (None, "")
                )
                if quote:
                    detailed_scoring_refs.append(
                        make_evidence_ref(
                            page=sub.get("source_page") or dim.get("source_page"),
                            quote=quote,
                            field_path=(
                                f"scoring.dimensions[{dim_i}]"
                                f".sub_items[{sub_i}]"
                            ),
                        )
                    )

        for ch in outline:
            source = ch.get("source")
            if source == "k12":
                ch["requirement_refs"] = k12_refs[:1]
                ch["scoring_refs"] = []
            elif source == "scoring":
                ch["requirement_refs"] = []
                ch["scoring_refs"] = (detailed_scoring_refs or scoring_refs)[:3]
            else:
                ch["requirement_refs"] = k12_refs[:1] if k12_refs else []
                ch["scoring_refs"] = []
        return outline

    # ================================================================
    # 阶段 3：自然语言理解提纲修改指令
    # ================================================================

    def interpret_outline_command(
        self,
        current_outline: list[dict[str, Any]],
        user_msg: str,
    ) -> dict[str, Any]:
        """
        LLM 解析用户对提纲的自然语言修改指令。

        替代固定正则（删除第N章 / 加一章 [标题] / 改 [旧] 为 [新]），
        让用户可以口语化地说："把第3章改成实施保障"、
        "技术方案那章加一个数据迁移的小节"、"业绩案例那章太长了，删了吧"。

        Returns dict, action 字段决定下游怎么处理:
          accept            → 接受当前提纲（不常用，orchestrator 单独处理"继续"）
          delete            → 删除某章 (chapter_no, optional chapter_title)
          add               → 新增章节 (title, category, after_chapter_no?)
          rename            → 重命名某章 (chapter_no, new_title)
          modify_subsection → 修改某章的小节
                              (chapter_no, sub_action in add/delete/rename,
                               subsection_title, new_subsection_title?)
          regenerate        → 让 AI 重新生成 (hint, 传回 generate_outline)
          unknown           → 指令不清楚 (message 给用户的回复)
        """
        # 把当前提纲压缩成 LLM 友好的形态（标号 + 标题 + 分类 + 小节标题）
        chapter_lines: list[str] = []
        for i, ch in enumerate(current_outline, 1):
            no = ch.get("no", i)
            title = ch.get("title", "")
            cat = ch.get("category", "")
            subs = ch.get("subsections") or []
            sub_titles = " / ".join(s.get("title", "") for s in subs if s.get("title"))
            line = f"  第{no}章 {title}（{cat}）"
            if sub_titles:
                line += f"  小节: {sub_titles}"
            chapter_lines.append(line)
        outline_text = "\n".join(chapter_lines) or "  （空）"

        prompt = f"""你是标书提纲修改助手。用户想修改当前提纲，用自然语言告诉你改什么。

当前提纲：
{outline_text}

用户指令：{user_msg}

请解析用户意图，从以下 action 中选一个，**严格按 JSON 返回**：

1) accept  — 用户表示认可（"可以"、"确认"、"看着行"等），无修改
   {{{{}}}}
2) delete — 删除某章。必带 chapter_no（数字，从 1 开始）+ chapter_title
   （当前章节标题，用于二次校验）。
   {{{{ "action": "delete", "chapter_no": 3, "chapter_title": "技术方案" }}}}
3) add — 新增章节。必带 title，可选 category（必须是 6 个标准分类之一：
   01_公司资质 / 02_业绩案例 / 03_技术方案 / 04_实施方案 / 05_商务文件 / 06_其他）
   和 after_chapter_no（在第 N 章之后插入；缺省追加到末尾）
   {{{{ "action": "add", "title": "数据迁移方案", "category": "03_技术方案", "after_chapter_no": 3 }}}}
4) rename — 重命名某章。必带 chapter_no + chapter_title + new_title
   {{{{ "action": "rename", "chapter_no": 3, "chapter_title": "技术方案", "new_title": "实施保障方案" }}}}
5) modify_subsection — 修改某章的小节。必带 chapter_no + chapter_title +
   sub_action (add / delete / rename)、subsection_title（当前小节标题或新增小节标题）、
   可选 new_subsection_title（仅 rename 时用）
   {{{{ "action": "modify_subsection", "chapter_no": 3, "chapter_title": "技术方案",
       "sub_action": "add", "subsection_title": "数据迁移方案" }}}}
6) regenerate — 用户要求 AI 重新生成/重排。必带 hint
   {{{{ "action": "regenerate", "hint": "技术方案那章细化成架构/接口/安全三个小节" }}}}
7) unknown — 指令不清楚。必带 message（要简洁、引导用户重说）
   {{{{ "action": "unknown", "message": "我没理解你的意思。可以说'删除第N章'、'加一章 xxx'、'把第N章改成 xxx'。" }}}}

**判断规则（重要）**：
- 用户说的章节编号（"第N章"）直接用 N 作 chapter_no。
- 用户用章节标题指代（"技术方案那章"、"业绩案例部分"）→ 你**必须**在当前提纲中
  找到对应章节并回填 chapter_no + chapter_title。如果当前提纲中**没有**这个名字的
  章节（用户记错了、章节已删、改过名），必须返回 unknown，message 告诉用户
  "找不到章节『技术方案』，当前有：公司资质/业绩案例/实施方案/..."。
- 如果指令可能有多重理解（如同时提到"加"和"删"），用 unknown 让用户重说。
- 用户的指令是建议/模糊的（"我觉得可以再细一点"）→ 用 regenerate + hint。
- chapter_title 必须**精确等于**当前提纲里该章节的 title 字符串。
- 只返回 JSON，不要任何其他文字。"""

        messages = [
            {"role": "system", "content": "你是结构化指令解析器。只输出 JSON。"},
            {"role": "user", "content": prompt},
        ]
        client = BidLLMClient()
        if not client.is_available:
            return {
                "action": "unknown",
                "message": "LLM 不可用，请说固定指令（删除第N章 / 加一章 [标题] / 改 [旧] 为 [新]）",
            }

        try:
            data = client.chat_json(messages, temperature=0.0, max_tokens=512)
        except Exception as e:
            logger.warning("LLM 提纲指令解析失败: %s", e)
            data = None

        if not data or "action" not in data:
            return {
                "action": "unknown",
                "message": "我没理解。能换个说法吗？比如：删除第3章 / 加一章 [标题] / 把第N章改成 [新标题]。",
            }

        # 基本校验 + 用提纲里的真实数据回填
        return self._sanitize_outline_command(data, current_outline)

    @staticmethod
    def _sanitize_outline_command(
        action: dict[str, Any],
        current_outline: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """校验 + 回填 LLM 输出的指令。

        关键校验：对于 delete/rename/modify_subsection，
        校验 chapter_no 指向的章节其 title 是否 == chapter_title。
        不一致 → 章节已被改名/删除/编号错位 → 改 unknown。
        """
        a = action.get("action")
        if a == "accept" or a == "regenerate" or a == "unknown":
            return action
        if a in ("delete", "rename", "modify_subsection"):
            no = action.get("chapter_no")
            title = action.get("chapter_title")
            # 反查：LLM 只给了 chapter_title 没给 chapter_no
            if no is None and title:
                for i, ch in enumerate(current_outline, 1):
                    if title == ch.get("title"):
                        no = ch.get("no", i)
                        break
            if not isinstance(no, int) or not (1 <= no <= len(current_outline)):
                return {
                    "action": "unknown",
                    "message": f"找不到第{action.get('chapter_no', '?')}章，当前只有 {len(current_outline)} 章。",
                }
            target = next(
                (ch for ch in current_outline if ch.get("no") == no), None
            )
            if not target:
                return {
                    "action": "unknown",
                    "message": f"找不到第{no}章。",
                }
            # 一致性校验：title 必须精确匹配（不接受模糊包含）
            if title and title != target.get("title"):
                available = " / ".join(
                    ch.get("title", "") for ch in current_outline
                )
                return {
                    "action": "unknown",
                    "message": (
                        f"找不到章节「{title}」。"
                        f"当前有：{available}"
                    ),
                }
            action["chapter_no"] = no
            action["chapter_title"] = target.get("title")
            return action
        if a == "add":
            title = (action.get("title") or "").strip()
            if not title:
                return {
                    "action": "unknown",
                    "message": "新增章节需要标题，比如：'加一章 数据迁移方案'",
                }
            cat = action.get("category") or "06_其他"
            if cat not in STANDARD_CATEGORIES:
                cat = "06_其他"
            after = action.get("after_chapter_no")
            if not isinstance(after, int) or after < 0 or after > len(current_outline):
                after = len(current_outline)
            action["title"] = title
            action["category"] = cat
            action["after_chapter_no"] = after
            return action
        return {
            "action": "unknown",
            "message": "我没能解析这个指令。",
        }

    # ================================================================
    # 输出校验
    # ================================================================

    def validate_output(self, output: dict[str, Any]) -> bool:
        return (
            "chapters" in output and isinstance(output["chapters"], list)
        ) or (
            "outline" in output and isinstance(output["outline"], list)
        )


# ============================================================================
# 提纲静态验证（Phase 0 - Task 0.1）
# ============================================================================

def validate_outline(
    outline: list[dict[str, Any]],
    scoring: dict[str, Any],
    k12: str | None = None,
) -> dict[str, Any]:
    """
    提纲静态验证（不调用 LLM）。

    检查规则：
    1. 评分项覆盖度 — scoring.dimensions 里带独立分值的 sub_items 是否在提纲中有对应章节/小节
    2. 章节数量合理性 — 一级章节 3-10 个，每章小节 ≤10 个
    3. 分类多样性 — 6 个标准分类至少用了 4 个
    4. K12 模板遵从 — 如果 K12 是结构化目录，检查关键章节是否保留
    5. 重复检查 — 章节标题不重复，小节标题不与父章节重复

    Args:
        outline: 提纲（generate_outline 的输出）
        scoring: parsed_data 中的 scoring 模块
        k12: K12_章节模板要求字段值

    Returns:
        {
            "is_valid": bool,        # 是否有阻塞性错误
            "warnings": [str],       # ⚠️ 警告列表
            "errors": [str],         # ❌ 错误列表（阻塞性问题）
            "stats": {               # 统计信息
                "chapter_count": int,
                "subsection_count": int,
                "category_usage": dict,
                "scoring_coverage": float,
            }
        }
    """
    warnings: list[str] = []
    errors: list[str] = []

    if not outline:
        errors.append("提纲为空")
        return {
            "is_valid": False,
            "warnings": [],
            "errors": errors,
            "stats": {},
        }

    # ================================================================
    # 规则 1: 评分项覆盖度
    # ================================================================
    scoring_items_checked = 0
    scoring_items_missing = 0

    for dim in scoring.get("dimensions", []):
        for sub in dim.get("sub_items", []):
            score = sub.get("score", 0)
            if score == 0:
                continue  # 跳过无分值的项

            scoring_items_checked += 1
            sub_name = sub.get("name", "").strip()
            if not sub_name:
                continue

            # 在提纲的章节标题和小节标题中查找
            found = False
            for ch in outline:
                ch_title = ch.get("title", "")
                if sub_name in ch_title:
                    found = True
                    break
                # 检查小节
                for subsec in ch.get("subsections", []):
                    if sub_name in subsec.get("title", ""):
                        found = True
                        break
                if found:
                    break

            if not found:
                scoring_items_missing += 1
                warnings.append(
                    f"⚠️ 评分项『{sub_name}』({score}分) 未在提纲中找到对应章节"
                )

    # ================================================================
    # 规则 2: 章节数量合理性
    # ================================================================
    chapter_count = len(outline)
    subsection_count = sum(len(ch.get("subsections", [])) for ch in outline)

    if chapter_count < 3:
        warnings.append(
            f"⚠️ 一级章节只有 {chapter_count} 个，粒度可能太粗（建议 3-10 个）"
        )
    elif chapter_count > 10:
        warnings.append(
            f"⚠️ 一级章节有 {chapter_count} 个，可能过于细碎（建议 3-10 个）"
        )

    for ch in outline:
        subs = ch.get("subsections", [])
        if len(subs) > 10:
            warnings.append(
                f"⚠️ 第{ch.get('no')}章『{ch.get('title')}』有 {len(subs)} 个小节"
                f"（建议 ≤10，考虑拆分为多个一级章节）"
            )

    # ================================================================
    # 规则 3: 分类多样性
    # ================================================================
    category_usage = {}
    for ch in outline:
        cat = ch.get("category", "06_其他")
        category_usage[cat] = category_usage.get(cat, 0) + 1

    used_categories = len(category_usage)
    if used_categories < 3:
        warnings.append(
            f"⚠️ 只使用了 {used_categories} 个标准分类，章节可能分类不当"
            f"（建议使用 4-6 个分类）"
        )

    # 检查是否过度使用 06_其他
    other_count = category_usage.get("06_其他", 0)
    if other_count > chapter_count * 0.4:
        warnings.append(
            f"⚠️ {other_count} 个章节归为『06_其他』，占比过高"
            f"（建议归入更具体的分类）"
        )

    # ================================================================
    # 规则 4: K12 模板遵从
    # ================================================================
    if k12 and len(k12) > 20:
        # 检查 K12 是否是结构化目录（包含"第一章"、"第二章"等）
        is_structured = any(
            pattern in k12
            for pattern in ["第一章", "第二章", "第1章", "第2章", "1.", "2."]
        )
        if is_structured:
            # 提取 K12 中的章节关键词（简单启发式）
            import re
            k12_chapters = re.findall(
                r"第[一二三四五六七八九十\d]+章\s*[：:]\s*([^\n、，。]+)",
                k12
            )
            if not k12_chapters:
                k12_chapters = re.findall(r"第[一二三四五六七八九十\d]+章\s+([^\n]+)", k12)

            # 检查是否保留了 K12 的关键章节
            outline_titles = {ch.get("title", "") for ch in outline}
            k12_missing = []
            for k12_ch in k12_chapters[:10]:  # 只检查前 10 章
                k12_ch = k12_ch.strip()
                if not k12_ch:
                    continue
                # 模糊匹配（允许部分包含）
                if not any(k12_ch[:5] in title for title in outline_titles):
                    k12_missing.append(k12_ch)

            if k12_missing and len(k12_missing) > len(k12_chapters) * 0.3:
                warnings.append(
                    f"⚠️ K12 要求的章节中有 {len(k12_missing)} 个未在提纲中体现，"
                    f"如：{', '.join(k12_missing[:3])}"
                )

    # ================================================================
    # 规则 5: 重复检查
    # ================================================================
    # 检查章节标题重复
    title_counts: dict[str, int] = {}
    for ch in outline:
        title = ch.get("title", "").strip()
        if title:
            title_counts[title] = title_counts.get(title, 0) + 1

    duplicates = [t for t, c in title_counts.items() if c > 1]
    if duplicates:
        errors.append(
            f"❌ 章节标题重复：{', '.join(f'『{t}』' for t in duplicates)}"
        )

    # 检查小节标题与父章节重复
    for ch in outline:
        ch_title = ch.get("title", "").strip()
        for sub in ch.get("subsections", []):
            sub_title = sub.get("title", "").strip()
            if sub_title == ch_title:
                warnings.append(
                    f"⚠️ 第{ch.get('no')}章『{ch_title}』的小节标题与章节标题完全相同"
                )
            elif sub_title and ch_title and sub_title in ch_title:
                warnings.append(
                    f"⚠️ 第{ch.get('no')}章『{ch_title}』的小节『{sub_title}』"
                    f"与章节标题重复（建议删除该小节或改为其他内容）"
                )

    # ================================================================
    # 统计信息
    # ================================================================
    scoring_coverage = 0.0
    if scoring_items_checked > 0:
        scoring_coverage = (
            (scoring_items_checked - scoring_items_missing) / scoring_items_checked
        )

    stats = {
        "chapter_count": chapter_count,
        "subsection_count": subsection_count,
        "category_usage": category_usage,
        "scoring_coverage": round(scoring_coverage, 2),
        "scoring_items_checked": scoring_items_checked,
        "scoring_items_missing": scoring_items_missing,
    }

    return {
        "is_valid": len(errors) == 0,
        "warnings": warnings,
        "errors": errors,
        "stats": stats,
    }
