"""
MatcherAgent — 材料匹配
将招标文件章节要求与材料库进行智能匹配
"""
from typing import Any

from agents.base import BaseAgent, AgentContext
from agents.bid_parser.schema import k_field_value

SYSTEM_PROMPT = """你是投标材料匹配专家。根据招标文件中的章节要求，从材料库中推荐最匹配的文档。

对每个章节：
1. 分析章节主题和关键词
2. 从材料库中检索相关性最高的材料
3. 给出匹配分数（高/中/低）和推荐理由
4. 如果没有匹配的材料，标记为"需新建"

返回 JSON 数组：[{chapter, material_id, material_title, match_score, reason}]"""


class MatcherAgent(BaseAgent):
    name = "matcher"
    description = "将招标文件章节要求与材料库进行智能匹配"
    system_prompt = SYSTEM_PROMPT
    temperature = 0.1

    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        """匹配材料。TODO: Phase 4 — 对材料库做 TF-IDF + 语义排序。"""
        parsed = ctx.parsed_data
        # K 字段新 shape：{value, source_page}，用 k_field_value 拿到字符串
        project_name = k_field_value(parsed.get("K01_项目名称")) or "未知项目"

        chapters = [
            {"chapter": "第一章 公司简介",
             "material_id": 1, "material_title": "公司简介模板",
             "match_score": "高", "reason": "标准版本可直接使用"},
            {"chapter": "第二章 业绩案例",
             "material_id": 2, "material_title": f"{project_name}HIS系统（2024）",
             "match_score": "高", "reason": "三甲医院HIS系统，匹配度高"},
            {"chapter": "第三章 技术方案",
             "material_id": 3, "material_title": "HIS技术方案v3",
             "match_score": "中", "reason": "最新版，覆盖招标要求"},
            {"chapter": "第四章 实施计划",
             "material_id": 4, "material_title": "标准实施方法论",
             "match_score": "中", "reason": "通用版本"},
        ]

        ctx.chapters = chapters
        ctx.error = None
        return {"chapters": chapters, "total": len(chapters)}

    def validate_output(self, output: dict[str, Any]) -> bool:
        return "chapters" in output and isinstance(output["chapters"], list)
