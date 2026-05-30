"""
ReviewerAgent — 终审检查
对标书初稿执行 C01-C10 10 项检查，主标和陪标都须审查
"""
from agents.base import BaseAgent, AgentContext

C01_C10_CHECKS = [
    ("C01_名称一致性", "招标人名称在正文各处是否一致"),
    ("C02_产品名称一致性", "产品名称在正文各处是否一致"),
    ("C03_时间一致性", "工期/节点描述是否一致"),
    ("C04_期限一致性", "投标截止时间与开标时间是否合理"),
    ("C05_金额一致性", "预算金额大小写/单位是否一致"),
    ("C06_人员一致性", "授权代表等人员信息是否一致"),
    ("C07_章节完整性", "是否覆盖所有要求的章节"),
    ("C08_星标项覆盖", "星标项是否全部响应"),
    ("C09_废标条款自查", "是否触及废标条款"),
    ("C10_资质引用有效性", "引用资质是否有效、未过期"),
]

# 陪标专属额外检查
SUB_BID_EXTRA_CHECKS = [
    ("SUB01_事实一致性", "日期/金额/名称不得偏离招标要求"),
    ("SUB02_商务资质完整性", "商务资质必须与主标完全一致"),
    ("SUB03_内容独立性", "不能与主标雷同度太高（措辞/结构须差异化）"),
]

SYSTEM_PROMPT = """你是标书质量审核专家。严格对照招标要求检查标书。

执行以下 10 项检查（C01-C10），每项输出：
- status: "pass" | "warning" | "fail"
- issue: 具体问题描述（pass 则空）
- suggestion: 修改建议（pass 则空）

对于陪标（sub），额外检查 3 项：事实一致性、商务资质完整性、内容独立性。

返回 JSON: {checks: [{check_id, check_name, status, issue, suggestion}], summary: {high, medium, low}}"""


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    description = "对标书初稿执行 C01-C10 终审检查（主标 + 陪标）"
    system_prompt = SYSTEM_PROMPT
    temperature = 0.0

    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        """执行终审检查。TODO: Phase 4 — 调用 DeepSeek 执行完整检查。"""
        is_sub = ctx.tender_type == "sub"

        checks = []
        for check_id, description in C01_C10_CHECKS:
            checks.append({
                "check_id": check_id,
                "check_name": description,
                "status": "pass",
                "issue": "",
                "suggestion": "",
            })

        # 添加一个示例警告，模拟发现问题
        checks[2]["status"] = "warning"  # C03 时间一致性
        checks[2]["issue"] = "第3章工期8个月，第7章写的是6个月"
        checks[2]["suggestion"] = "统一为8个月"

        if is_sub:
            for check_id, description in SUB_BID_EXTRA_CHECKS:
                checks.append({
                    "check_id": check_id,
                    "check_name": description,
                    "status": "pass",
                    "issue": "",
                    "suggestion": "",
                })

        summary = {
            "high": sum(1 for c in checks if c["status"] == "fail"),
            "medium": sum(1 for c in checks if c["status"] == "warning"),
            "low": sum(1 for c in checks if c["status"] == "pass"),
        }

        report = {"checks": checks, "summary": summary, "tender_type": ctx.tender_type}
        ctx.review_report = report
        ctx.error = None
        return report

    def validate_output(self, output: dict[str, Any]) -> bool:
        return "checks" in output and "summary" in output
