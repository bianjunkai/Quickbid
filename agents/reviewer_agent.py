"""
ReviewerAgent — 终审检查
对标书初稿执行 C01-C10 10 项检查，主标和陪标都须审查
"""
import json
from typing import Any

from agents.base import BaseAgent, AgentContext
from agents.bid_parser.pipeline import BidLLMClient
from models import Project, Tender, get_session

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
        """执行终审检查，返回固定 schema。"""
        is_sub = ctx.tender_type == "sub"
        draft_content, project_context, load_error = self._load_review_context(ctx)
        if load_error:
            report = self._error_report(load_error, ctx.tender_type)
            ctx.review_report = report
            ctx.error = load_error
            return report

        client = BidLLMClient()
        if not client.is_available:
            error = "LLM 不可用 (TENDER_DEEPSEEK_API_KEY 未设置)"
            report = self._error_report(error, ctx.tender_type)
            ctx.review_report = report
            ctx.error = error
            return report

        expected_checks = C01_C10_CHECKS + (SUB_BID_EXTRA_CHECKS if is_sub else [])
        prompt = self._build_prompt(
            tender_type=ctx.tender_type,
            project_context=project_context,
            draft_content=draft_content,
            expected_checks=expected_checks,
        )
        result = client.chat_json(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self.temperature,
            max_tokens=4096,
        )

        report = self._normalize_report(result, expected_checks, ctx.tender_type)
        ctx.review_report = report
        ctx.error = None if not report.get("error") else report["error"]
        return report

    def _load_review_context(self, ctx: AgentContext) -> tuple[str, dict[str, Any], str | None]:
        if not ctx.tender_id:
            return "", {}, "缺少 tender_id，无法终审"

        session = get_session()
        tender = session.get(Tender, ctx.tender_id)
        if not tender:
            return "", {}, "标书不存在，无法终审"
        if not tender.draft_path:
            return "", {}, "标书尚未生成 draft.md，无法终审"

        try:
            with open(tender.draft_path, encoding="utf-8") as f:
                draft_content = f.read()
        except Exception as e:
            return "", {}, f"读取 draft.md 失败: {e}"

        project_context: dict[str, Any] = {}
        project = session.get(Project, tender.project_id)
        if project:
            project_context = {
                "project_name": project.project_name or project.name,
                "tender_no": project.tender_no,
                "budget": project.budget,
                "deadline": project.deadline.isoformat() if project.deadline else None,
                "open_time": project.open_time.isoformat() if project.open_time else None,
            }
            if project.parsed_data:
                try:
                    project_context["parsed_data"] = json.loads(project.parsed_data)
                except json.JSONDecodeError:
                    project_context["parsed_data"] = {}

        return draft_content, project_context, None

    def _build_prompt(
        self,
        tender_type: str,
        project_context: dict[str, Any],
        draft_content: str,
        expected_checks: list[tuple[str, str]],
    ) -> str:
        checks_text = "\n".join(
            f"- {check_id}: {description}" for check_id, description in expected_checks
        )
        context_json = json.dumps(project_context, ensure_ascii=False, indent=2)
        return f"""# 标书类型
{tender_type}

# 必须执行的检查项
{checks_text}

# 招标/项目信息
{context_json}

# 标书初稿 Markdown
{draft_content[:30000]}

# 输出要求
只返回 JSON，不要 Markdown 代码块。schema 固定如下：
{{
  "checks": [
    {{
      "check_id": "string",
      "check_name": "string",
      "status": "pass | warning | fail",
      "issue": "string",
      "suggestion": "string"
    }}
  ],
  "summary": {{
    "high": 0,
    "medium": 0,
    "low": 0
  }}
}}
"""

    def _normalize_report(
        self,
        result: dict[str, Any] | None,
        expected_checks: list[tuple[str, str]],
        tender_type: str,
    ) -> dict[str, Any]:
        if not isinstance(result, dict):
            return self._error_report("LLM 未返回有效 JSON 审查结果", tender_type)

        checks = []
        by_id = {
            c.get("check_id"): c
            for c in result.get("checks", [])
            if isinstance(c, dict) and c.get("check_id")
        }
        for check_id, description in expected_checks:
            raw = by_id.get(check_id, {})
            status = raw.get("status", "warning")
            if status not in ("pass", "warning", "fail"):
                status = "warning"
            checks.append({
                "check_id": check_id,
                "check_name": raw.get("check_name") or description,
                "status": status,
                "issue": raw.get("issue") or "",
                "suggestion": raw.get("suggestion") or "",
            })

        summary = {
            "high": sum(1 for c in checks if c["status"] == "fail"),
            "medium": sum(1 for c in checks if c["status"] == "warning"),
            "low": sum(1 for c in checks if c["status"] == "pass"),
        }
        return {"checks": checks, "summary": summary, "tender_type": tender_type}

    def _error_report(self, error: str, tender_type: str) -> dict[str, Any]:
        checks = []
        expected_checks = C01_C10_CHECKS + (
            SUB_BID_EXTRA_CHECKS if tender_type == "sub" else []
        )
        for idx, (check_id, description) in enumerate(expected_checks):
            checks.append({
                "check_id": check_id,
                "check_name": description,
                "status": "fail" if idx == 0 else "warning",
                "issue": error if idx == 0 else "未执行：终审前置条件未满足",
                "suggestion": "配置 LLM、生成 draft.md 后重新终审" if idx == 0 else "",
            })
        summary = {
            "high": sum(1 for c in checks if c["status"] == "fail"),
            "medium": sum(1 for c in checks if c["status"] == "warning"),
            "low": 0,
        }
        return {
            "checks": checks,
            "summary": summary,
            "tender_type": tender_type,
            "error": error,
        }

    def validate_output(self, output: dict[str, Any]) -> bool:
        return "checks" in output and "summary" in output
