"""
SubBidAgent — 陪标生成
独立生成陪标文件（与主标内容不同但事实一致），产出须经 ReviewerAgent 审查
"""
from typing import Any

from agents.base import BaseAgent, AgentContext

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
        """生成陪标。TODO: Phase 4 — 调用 DeepSeek 生成完整陪标。"""
        project_name = ctx.parsed_data.get("K01_项目名称", "招标项目")

        retry_note = ""
        if fix_issues:
            issues_desc = "\n".join(
                f"- {c['check_id']}: {c['issue']} → {c['suggestion']}"
                for c in fix_issues.get("checks", [])
                if c["status"] in ("fail", "warning")
            )
            retry_note = f"\n\n> ⚠️ 根据审查意见重新生成。修正项：\n{issues_desc}"

        draft = f"""# {project_name} — 投标文件（陪标）

## 商务资质
> 以下内容与主标完全一致

（商务资质材料逐字复制）

## 技术方案

本方案采用分布式微服务架构，结合云计算平台实现灵活扩展...

## 实施计划

项目分为需求分析、系统设计、开发测试、上线部署四个阶段...

{retry_note}

> 陪标初稿待 AI 生成（Phase 4）
"""

        ctx.sub_draft_content = draft
        ctx.tender_type = "sub"
        ctx.error = None
        return {"content": draft, "tender_type": "sub"}

    def validate_output(self, output: dict[str, Any]) -> bool:
        return "content" in output and len(output["content"]) > 0
