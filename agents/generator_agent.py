"""
GeneratorAgent — 标书初稿生成（Phase 4 实装）

策略：逐章 LLM 调用 + 拼装。每章单独调一次 BidLLMClient：
  - 输入：项目 K01 名称、K08 技术要求（前 1500 字符）、K10 星标项（前 8 项）、
         outline 章节信息、关联材料全文（从 file_path 读取,head 6000 + tail 2000）
  - 输出：单章 Markdown
  - 失败：placeholder 占位 + 记录，连续 3 章失败则中止

完成后输出完整 draft Markdown（cover + 目录 + 各章 + 偏离表占位），由 Orchestrator
落盘到 projects/{ts}_{name}/main/ 目录。
"""
import logging
from pathlib import Path
from typing import Any

from agents.base import BaseAgent, AgentContext
from agents.bid_parser.pdf_extractor import extract_file_text
from agents.bid_parser.pipeline import BidLLMClient
from agents.bid_parser.schema import k_field_value, k_field_items_with_pages

logger = logging.getLogger(__name__)

# 截断/采样常量
MAX_MATERIAL_HEAD_CHARS = 6000
MAX_MATERIAL_TAIL_CHARS = 2000
MAX_K08_CHARS = 1500
MAX_K10_ITEMS = 8
LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 4096
MAX_CONSECUTIVE_FAILURES = 3

CHAPTER_SYSTEM_PROMPT = """你是医院信息化标书撰写专家。

写作铁律:
1. 事实信息(日期/金额/名称/证书号)必须与招标要求和材料一致,不得编造
2. 引用材料时尽量保留材料原文表述,不要无中生有
3. 缺失细节用 [待补充:xxx] 占位,绝不编造
4. 使用正式、专业的标书语言
5. 输出 Markdown,严格按 outline 给定的章节结构
6. 直接给正文,不要任何解释文字或代码块包裹"""


class GeneratorAgent(BaseAgent):
    name = "generator"
    description = "根据确认的材料和章节结构生成标书初稿（逐章 LLM 拼装）"
    system_prompt = CHAPTER_SYSTEM_PROMPT
    temperature = LLM_TEMPERATURE

    # ================================================================
    # 主入口
    # ================================================================

    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        outline = ctx.outline or []
        if not outline:
            ctx.error = "提纲为空，无法生成"
            return {
                "content": "",
                "chapters": [],
                "chapters_count": 0,
                "errors": ["提纲为空"],
                "failed": True,
                "outline": [],
            }

        parsed = ctx.parsed_data or {}
        client = BidLLMClient()
        if not client.is_available:
            error = "LLM 不可用 (TENDER_DEEPSEEK_API_KEY 未设置)"
            ctx.error = error
            return {
                "content": "",
                "chapters": [],
                "chapters_count": 0,
                "errors": [error],
                "failed": True,
                "outline": outline,
            }

        # 章节-材料映射用 dict lookup,不假设顺序
        chapters_by_id = {
            ch.get("chapter_id"): ch for ch in (ctx.chapters or []) if ch.get("chapter_id")
        }
        materials_by_path = self._load_materials(chapters_by_id.values())

        k08 = self._truncate(k_field_value(parsed.get("K08_技术要求")), MAX_K08_CHARS)
        k10 = [
            item for item, _page in
            k_field_items_with_pages(parsed.get("K10_星标项"))
        ][:MAX_K10_ITEMS]
        project_name = k_field_value(parsed.get("K01_项目名称")) or "招标项目"

        assembled: list[dict[str, Any]] = []
        errors: list[str] = []
        consecutive_fails = 0
        aborted = False

        for ch_outline in outline:
            cid = ch_outline.get("id", "")
            match = chapters_by_id.get(cid) or {}
            file_path = match.get("file_path")
            material = materials_by_path.get(file_path) if file_path else None

            try:
                content = self._generate_chapter(
                    project_name=project_name,
                    chapter=ch_outline,
                    match=match,
                    material=material,
                    k08=k08,
                    k10=k10,
                )
                chapter_error = None
                consecutive_fails = 0
            except Exception as e:
                logger.warning("章节 '%s' 生成失败: %s", ch_outline.get("title"), e)
                content = self._placeholder_chapter(ch_outline, match, str(e))
                chapter_error = f"{type(e).__name__}: {e}"
                errors.append(f"{ch_outline.get('title', cid)}: {chapter_error}")
                consecutive_fails += 1
                if consecutive_fails >= MAX_CONSECUTIVE_FAILURES:
                    ctx.error = (
                        f"连续 {MAX_CONSECUTIVE_FAILURES} 章生成失败,中止: "
                        f"{'; '.join(errors[-MAX_CONSECUTIVE_FAILURES:])}"
                    )
                    aborted = True
                    break

            assembled.append({
                "chapter_id": cid,
                "no": ch_outline.get("no"),
                "title": ch_outline.get("title", ""),
                "volume": ch_outline.get("volume", "other"),
                "category": ch_outline.get("category", ""),
                "subsections": ch_outline.get("subsections", []) or [],
                "content": content,
                "file_path": file_path,
                "material_title": match.get("material_title", ""),
                "match_score": match.get("match_score", ""),
                "error": chapter_error,
            })

        draft_md = self._assemble_markdown(project_name, assembled, parsed)
        ctx.draft_content = draft_md
        ctx.error = ctx.error or ("; ".join(errors) if errors else None)

        return {
            "content": draft_md,
            "chapters": assembled,
            "chapters_count": len(assembled),
            "errors": errors,
            "failed": aborted,
            "aborted": aborted,
            "outline": outline,
        }

    # ================================================================
    # 单章 LLM 调用
    # ================================================================

    def _generate_chapter(
        self,
        project_name: str,
        chapter: dict[str, Any],
        match: dict[str, Any],
        material: dict[str, Any] | None,
        k08: str,
        k10: list[str],
    ) -> str:
        client = BidLLMClient()
        if not client.is_available:
            raise RuntimeError("LLM 不可用 (TENDER_DEEPSEEK_API_KEY 未设置)")

        material_block = self._format_material(material)
        subsections = chapter.get("subsections") or []
        sub_titles = [
            s.get("title", "").strip()
            for s in subsections
            if s.get("title", "").strip()
        ]
        chapter_no = chapter.get("no", "?")
        chapter_title = chapter.get("title", "")
        category = chapter.get("category", "")

        user_prompt = f"""# 标书项目
{project_name}

# 当前章节
第{chapter_no}章: {chapter_title}
分类: {category}

# 必须包含的小节（按顺序输出,小节标题字符串必须精确匹配）
{chr(10).join(f"{i+1}. {t}" for i, t in enumerate(sub_titles)) if sub_titles else "（无小节,直接展开正文）"}

# 关联材料
{material_block}

# 招标技术要求摘要
{k08 or "（无）"}

# 关键响应项（星标/否决项）
{chr(10).join(f"- {item}" for item in k10) if k10 else "（无）"}

# 输出要求
- 一级标题: ## 第{chapter_no}章 {chapter_title}
- 二级标题: ### {{{{小节标题}}}}（必须与上面小节列表精确一致;无小节则用 ### 小标题）
- 引用材料的具体数据/案例/证书号
- 缺失细节用 [待补充:xxx] 占位
- 不要编造日期/金额/名称/证书号
- 引用材料:在章节末尾加一行"参考材料:{match.get('material_title', '无')}"
- 直接给正文,不要任何解释文字或 ```markdown ``` 包裹"""

        messages = [
            {"role": "system", "content": CHAPTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        text = client.chat(
            messages,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
        if not text or not text.strip():
            raise RuntimeError("LLM 返回空")
        return self._strip_code_fence(text.strip())

    def _format_material(self, material: dict[str, Any] | None) -> str:
        """材料格式:title/category + head 6000 + tail 2000 + 显式省略标记。"""
        if not material:
            return "（无匹配材料,需根据招标要求撰写）"
        title = material.get("title") or "未命名材料"
        category = material.get("category") or ""
        body = (material.get("content") or "").strip()
        error = material.get("error")
        if not body:
            suffix = f"\n读取失败:{error}" if error else "\n（材料内容为空）"
            return f"【{title}】({category}){suffix}"

        body_block = ""
        if body:
            total = len(body)
            if total <= MAX_MATERIAL_HEAD_CHARS + MAX_MATERIAL_TAIL_CHARS:
                body_block = body
            else:
                head = body[:MAX_MATERIAL_HEAD_CHARS]
                tail = body[-MAX_MATERIAL_TAIL_CHARS:]
                body_block = (
                    f"{head}\n\n"
                    f"[... 材料中间内容省略（共 {total} 字符）...]\n\n"
                    f"{tail}"
                )

        parts = [f"【{title}】({category})"]
        file_path = material.get("file_path")
        if file_path:
            parts.append(f"来源文件: {file_path}")
        if body_block:
            parts.append(body_block)
        return "\n\n".join(parts)

    # ================================================================
    # 失败占位章节
    # ================================================================

    def _placeholder_chapter(
        self,
        chapter: dict[str, Any],
        match: dict[str, Any] | None,
        reason: str,
    ) -> str:
        title = chapter.get("title", "未命名章节")
        no = chapter.get("no", "?")
        subs = chapter.get("subsections") or []
        mat_title = (match or {}).get("material_title", "无")

        lines = [
            f"## 第{no}章 {title}",
            "",
            f"> ⚠️ 本章初稿生成失败: {reason}",
            f"> 关联材料: {mat_title}",
            "",
        ]
        if subs:
            for s in subs:
                lines.append(f"### {s.get('title', '未命名小节')}")
                lines.append("")
                lines.append("[待补充:本章内容]")
                lines.append("")
        else:
            lines.append("[待补充:本章内容]")
        return "\n".join(lines)

    # ================================================================
    # 拼装最终 Markdown
    # ================================================================

    def _assemble_markdown(
        self,
        project_name: str,
        chapters: list[dict[str, Any]],
        parsed: dict[str, Any],
    ) -> str:
        k01 = k_field_value(parsed.get("K01_项目名称")) or project_name
        k02 = k_field_value(parsed.get("K02_招标编号")) or ""
        k03 = k_field_value(parsed.get("K03_招标人")) or ""
        k05 = k_field_value(parsed.get("K05_投标截止时间")) or ""

        parts: list[str] = [
            f"# {k01} — 投标文件（主标）",
            "",
            "## 项目信息",
            "",
            f"- **项目名称**: {k01}",
        ]
        if k02:
            parts.append(f"- **招标编号**: {k02}")
        if k03:
            parts.append(f"- **招标人**: {k03}")
        if k05:
            parts.append(f"- **投标截止时间**: {k05}")
        parts.append("")

        parts.append("## 目录")
        parts.append("")
        for ch in chapters:
            no = ch.get("no", "?")
            title = ch.get("title", "")
            parts.append(f"- 第{no}章 {title}")
        parts.append("")

        for ch in chapters:
            parts.append(ch.get("content", "").rstrip())
            parts.append("")
            parts.append("---")
            parts.append("")

        parts.extend([
            "## 附录 A: 商务/技术条款偏离表",
            "",
            "> 详见同目录 `deviation.md`。系统会依据招标解析字段生成商务/技术条款偏离表。",
            "",
        ])

        return "\n".join(parts)

    # ================================================================
    # 辅助
    # ================================================================

    def _load_materials(self, matches) -> dict[str, dict[str, Any]]:
        """按 MatcherAgent 给出的 file_path 读取材料正文，不依赖数据库 Material。"""
        result: dict[str, dict[str, Any]] = {}
        for match in matches:
            file_path = match.get("file_path")
            if not file_path or file_path in result:
                continue
            path = Path(file_path)
            material = {
                "file_path": file_path,
                "title": match.get("material_title") or path.stem,
                "category": match.get("category") or path.parent.name,
                "content": "",
            }
            try:
                suffix = path.suffix.lower()
                if suffix == ".md":
                    material["content"] = path.read_text(encoding="utf-8")
                elif suffix == ".docx":
                    material["content"] = extract_file_text(str(path))
                else:
                    material["error"] = f"不支持的材料格式: {suffix or 'unknown'}"
            except Exception as e:
                material["error"] = str(e)
            result[file_path] = material
        return result

    @staticmethod
    def _truncate(s: str | None, n: int) -> str:
        if not s:
            return ""
        s = str(s)
        if len(s) <= n:
            return s
        return s[:n] + "..."

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """去掉 LLM 偶尔包裹的 ``` 围栏。"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        return text.strip()

    def validate_output(self, output: dict[str, Any]) -> bool:
        return "content" in output and "chapters" in output
