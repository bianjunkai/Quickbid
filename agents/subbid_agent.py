"""
SubBidAgent — 陪标生成
独立生成陪标文件（与主标内容不同但事实一致），产出须经 ReviewerAgent 审查
"""
import json
from pathlib import Path
from typing import Any

from agents.base import BaseAgent, AgentContext
from agents.bid_parser.pipeline import BidLLMClient
from agents.bid_parser.schema import k_field_value
from models import Project, Tender, get_session

SYSTEM_PROMPT = """你是投标文件撰写专家。生成一份独立风格的陪标文件。

要求：
1. 商务资质部分逐字复制主标内容（资质不可变）
2. 其余章节独立生成，结构和措辞与主标刻意差异化（降低雷同度）
3. 所有事实信息（金额、日期、名称）与招标要求严格一致，不得偏离
4. 使用 Markdown 格式

输出完整的陪标初稿。"""


class SubBidAgent(BaseAgent):
    name = "subbid"
    description = "独立生成陪标文件，商务资质逐字复制，其余章节独立生成"
    system_prompt = SYSTEM_PROMPT
    temperature = 0.5

    def execute(self, ctx: AgentContext, fix_issues: dict = None) -> dict[str, Any]:
        """生成陪标。基于主标和招标事实调用 DeepSeek，失败时显式返回错误。"""
        project_name = k_field_value(ctx.parsed_data.get("K01_项目名称")) or "招标项目"
        main_draft, project_context, load_error = self._load_main_context(ctx)
        if load_error:
            ctx.error = load_error
            return {
                "content": "",
                "tender_type": "sub",
                "failed": True,
                "errors": [load_error],
            }

        client = BidLLMClient()
        if not client.is_available:
            error = "LLM 不可用 (TENDER_DEEPSEEK_API_KEY 未设置)"
            ctx.error = error
            return {
                "content": "",
                "tender_type": "sub",
                "failed": True,
                "errors": [error],
            }

        prompt = self._build_prompt(
            project_name=project_name,
            parsed_data=ctx.parsed_data or {},
            project_context=project_context,
            main_draft=main_draft,
            fix_issues=fix_issues,
        )
        text = client.chat(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=8192,
        )
        if not text or not text.strip():
            error = "LLM 返回空，陪标生成失败"
            ctx.error = error
            return {
                "content": "",
                "tender_type": "sub",
                "failed": True,
                "errors": [error],
            }

        draft = self._strip_code_fence(text.strip())
        ctx.sub_draft_content = draft
        ctx.tender_type = "sub"
        ctx.error = None
        return {"content": draft, "tender_type": "sub", "errors": []}

    def _load_main_context(
        self,
        ctx: AgentContext,
    ) -> tuple[str, dict[str, Any], str | None]:
        """读取主标 draft 和项目上下文。ctx.tender_id 在陪标前应指向主标。"""
        if ctx.draft_content:
            main_draft = ctx.draft_content
        else:
            if not ctx.tender_id:
                return "", {}, "缺少主标 tender_id，无法生成陪标"
            session = get_session()
            tender = session.get(Tender, ctx.tender_id)
            if not tender:
                return "", {}, "主标不存在，无法生成陪标"
            if tender.type != "main":
                return "", {}, "当前 tender 不是主标，无法作为陪标依据"
            if not tender.draft_path:
                return "", {}, "主标尚未生成 draft.md，无法生成陪标"
            path = Path(tender.draft_path)
            if not path.exists():
                return "", {}, f"主标 draft.md 不存在: {path}"
            main_draft = path.read_text(encoding="utf-8")

        project_context: dict[str, Any] = {}
        if ctx.project_id:
            session = get_session()
            project = session.get(Project, ctx.project_id)
            if project:
                project_context = {
                    "project_name": project.project_name or project.name,
                    "tender_no": project.tender_no,
                    "budget": project.budget,
                    "deadline": project.deadline.isoformat() if project.deadline else None,
                    "open_time": project.open_time.isoformat() if project.open_time else None,
                }
        return main_draft, project_context, None

    def _build_prompt(
        self,
        project_name: str,
        parsed_data: dict[str, Any],
        project_context: dict[str, Any],
        main_draft: str,
        fix_issues: dict | None,
    ) -> str:
        parsed_json = json.dumps(parsed_data, ensure_ascii=False, indent=2)[:12000]
        project_json = json.dumps(project_context, ensure_ascii=False, indent=2)
        retry_block = "无"
        if fix_issues:
            retry_items = [
                f"- {c.get('check_id')}: {c.get('issue')} -> {c.get('suggestion')}"
                for c in fix_issues.get("checks", [])
                if c.get("status") in ("fail", "warning")
            ]
            retry_block = "\n".join(retry_items) if retry_items else "无"

        return f"""# 项目
{project_name}

# 项目结构化信息
{project_json}

# 招标解析字段
{parsed_json}

# 主标 Markdown（事实基准，商务资质需保持一致）
{main_draft[:30000]}

# 上轮终审问题（如有）
{retry_block}

# 输出要求
- 输出完整 Markdown 陪标初稿，标题为“{project_name} — 投标文件（陪标）”
- 商务资质、企业资质、证书、授权、金额、日期、项目名称、招标编号等事实必须与主标和招标解析字段一致
- 技术方案、实施方案、服务方案等非资质章节要换一种组织方式和措辞，避免与主标雷同
- 不确定的信息使用 [待补充:xxx]，不得编造
- 不要输出解释，不要用代码块包裹
"""

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return text

    def validate_output(self, output: dict[str, Any]) -> bool:
        return not output.get("failed") and "content" in output and len(output["content"]) > 0
