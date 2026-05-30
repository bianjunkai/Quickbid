"""
ParserAgent — 招标文件解析
从 PDF/DOCX 文本中提取 K01-K14 结构化信息
"""
import json
from pathlib import Path
from agents.base import BaseAgent, AgentContext

K01_K14_SCHEMA = {
    "K01_项目名称": "string",
    "K02_招标编号": "string",
    "K03_招标人": "string",
    "K04_预算金额": "string",
    "K05_投标截止时间": "string",
    "K06_开标时间": "string",
    "K07_评分标准": "string",
    "K08_技术要求": "string",
    "K09_商务资质要求": "string",
    "K10_星标项": "list",
    "K11_废标条款": "list",
    "K12_章节模板要求": "string",
    "K13_偏离表格式要求": "string",
    "K14_演示要求": "string",
}

SYSTEM_PROMPT = """你是招标文件分析专家。请从以下招标文件内容中提取关键信息。

返回严格的 JSON 格式，包含以下字段：
- K01_项目名称: string
- K02_招标编号: string
- K03_招标人: string
- K04_预算金额: string (含单位)
- K05_投标截止时间: string
- K06_开标时间: string
- K07_评分标准: string (简要概括)
- K08_技术要求: string (简要概括)
- K09_商务资质要求: string
- K10_星标项: string[] (带★标记的条款)
- K11_废标条款: string[]
- K12_章节模板要求: string
- K13_偏离表格式要求: string
- K14_演示要求: string

如果某字段在文件中未找到，请填写"未找到"。仅返回 JSON，不要有其他文字。"""


class ParserAgent(BaseAgent):
    name = "parser"
    description = "从招标文件中提取 K01-K14 结构化信息"
    system_prompt = SYSTEM_PROMPT
    temperature = 0.0

    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        """解析招标文件。先从 DB 获取文件路径，提取文本后调用 DeepSeek。"""
        # TODO: Phase 4 — 接入 DeepSeek API
        parsed = {
            "K01_项目名称": ctx.parsed_data.get("K01_项目名称") or "待提取",
            "K02_招标编号": "HN-2026-0501",
            "K03_招标人": "xx省人民医院",
            "K04_预算金额": "850万元",
            "K05_投标截止时间": "2026-06-15 14:00",
            "K06_开标时间": "2026-06-15 14:00",
            "K07_评分标准": "技术60%+商务40%",
            "K08_技术要求": "覆盖HIS/EMR/LIS/PACS系统",
            "K09_商务资质要求": "需提供等保证明、三甲医院案例≥3个",
            "K10_星标项": ["★ 必须具备等保三级", "★ 演示时间30分钟"],
            "K11_废标条款": ["证书过期视为废标", "偏离超过20%视为废标"],
            "K12_章节模板要求": "共8章，详见第三章",
            "K13_偏离表格式要求": "须使用招标方指定格式",
            "K14_演示要求": "需现场演示，PPT不超过20页",
        }

        ctx.parsed_data = parsed
        ctx.error = None
        return parsed

    def validate_output(self, output: dict[str, Any]) -> bool:
        required_keys = [f"K{i:02d}" for i in range(1, 15)]
        for key_template in required_keys:
            found = any(k.startswith(key_template) for k in output)
            if not found:
                return False
        return True
