"""
GeneratorAgent — 标书初稿生成
根据确认的材料和章节结构生成标书初稿
"""
from agents.base import BaseAgent, AgentContext

SYSTEM_PROMPT = """你是医疗信息化标书撰写专家。根据以下材料内容撰写专业标书章节。

要求：
1. 使用正式、专业的标书语言
2. 事实信息（日期、金额、名称）必须与招标要求一致，不得编造
3. 引用材料中的案例和经验
4. 按章节结构输出，使用 Markdown 格式
5. 生成偏离表（对照 K13 格式要求）
6. 星标项（K10）必须全部响应

输出 Markdown 格式的完整标书初稿。"""


class GeneratorAgent(BaseAgent):
    name = "generator"
    description = "根据确认的材料和章节结构生成标书初稿"
    system_prompt = SYSTEM_PROMPT
    temperature = 0.3

    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        """生成标书初稿。TODO: Phase 4 — 调用 DeepSeek 生成完整标书。"""
        project_name = ctx.parsed_data.get("K01_项目名称", "招标项目")
        chapters = ctx.chapters

        # 构建章节预览
        chapter_preview = "\n".join(
            f"- {ch['chapter']}: {ch['material_title']}"
            for ch in chapters
        )

        draft = f"""# {project_name} — 投标文件

## 核心亮点
- 基于 {len(chapters)} 个章节材料拼接
- 技术方案突出「云架构+微服务」
- 偏离表已生成，共12项响应

{chapter_preview}

## 注意事项
- 第3章工期描述已按招标要求修正
- 第5章金额已统一

> 初稿待 AI 生成（Phase 4）
"""

        ctx.draft_content = draft
        ctx.error = None
        return {"content": draft, "chapters_count": len(chapters)}

    def validate_output(self, output: dict[str, Any]) -> bool:
        return "content" in output and len(output["content"]) > 0
