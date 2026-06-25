"""
ReviewerAgent — 终审检查
对标书初稿执行 C01-C10 10 项检查，主标和陪标都须审查
"""
import json
import re
from pathlib import Path
from typing import Any

from agents.base import BaseAgent, AgentContext
from agents.bid_parser.evidence import evidence_from_k_field, make_evidence_ref
from agents.bid_parser.pipeline import BidLLMClient
from agents.bid_parser.schema import k_field_items_with_pages, k_field_value
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
- requirement_ref: 招标要求来源 {page, quote, field_path}
- draft_ref: 标书问题位置 {path, heading}

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

        deterministic_checks = self._run_deterministic_checks(
            draft_content=draft_content,
            project_context=project_context,
            tender_type=ctx.tender_type,
        )

        client = BidLLMClient()
        if not client.is_available:
            error = "LLM 不可用 (TENDER_DEEPSEEK_API_KEY 未设置)"
            report = self._merge_deterministic_checks(
                self._error_report(error, ctx.tender_type),
                deterministic_checks,
            )
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
        try:
            result = client.chat_json(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=4096,
            )
        except Exception as e:
            error = f"LLM 语义审查失败: {type(e).__name__}: {e}"
            report = self._merge_deterministic_checks(
                self._error_report(error, ctx.tender_type),
                deterministic_checks,
            )
            ctx.review_report = report
            ctx.error = error
            return report

        report = self._normalize_report(result, expected_checks, ctx.tender_type)
        report = self._merge_deterministic_checks(report, deterministic_checks)
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
        if not draft_content.strip():
            return "", {}, "draft.md 为空，无法终审"

        project_context: dict[str, Any] = {}
        project = session.get(Project, tender.project_id)
        if project:
            project_context = {
                "project_name": project.project_name or project.name,
                "tender_no": project.tender_no,
                "budget": project.budget,
                "deadline": project.deadline.isoformat() if project.deadline else None,
                "open_time": project.open_time.isoformat() if project.open_time else None,
                "_draft_path": tender.draft_path,
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
      "suggestion": "string",
      "requirement_ref": {{"page": 1, "quote": "招标原文", "field_path": "K10_星标项.items[0]"}},
      "draft_ref": {{"path": "main/draft.md", "heading": "第3章 技术方案"}}
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
                "problem": raw.get("problem") or raw.get("issue") or "",
                "expected": raw.get("expected") or "",
                "actual": raw.get("actual") or "",
                "requirement_ref": raw.get("requirement_ref"),
                "draft_ref": raw.get("draft_ref"),
                "blocking": bool(raw.get("blocking")) if raw.get("blocking") is not None else status == "fail",
            })

        summary = {
            "high": sum(1 for c in checks if c["status"] == "fail"),
            "medium": sum(1 for c in checks if c["status"] == "warning"),
            "low": sum(1 for c in checks if c["status"] == "pass"),
        }
        return {
            "checks": checks,
            "issues": [c for c in checks if c["status"] in ("warning", "fail")],
            "summary": summary,
            "tender_type": tender_type,
        }

    def _run_deterministic_checks(
        self,
        draft_content: str,
        project_context: dict[str, Any],
        tender_type: str,
    ) -> list[dict[str, Any]]:
        parsed = project_context.get("parsed_data") or {}
        draft_path = self._display_draft_path(project_context.get("_draft_path"))
        checks: list[dict[str, Any]] = []

        outline = (
            parsed.get("_confirmed_outline")
            or parsed.get("_generated_outline")
            or []
        )
        for ch in outline:
            title = ch.get("title") or ""
            if title and title not in draft_content:
                checks.append(self._issue(
                    check_id="C07_章节完整性",
                    check_name="章节完整性",
                    problem=f"生成稿缺少一级章节：{title}",
                    expected=f"应包含章节「{title}」",
                    actual="draft.md 中未找到该章节标题",
                    suggestion=f"补充「{title}」章节，或回到提纲阶段调整。",
                    requirement_ref=self._first_ref(
                        ch.get("requirement_refs") or ch.get("scoring_refs")
                    ),
                    draft_ref={"path": draft_path, "heading": "目录"},
                ))
            for sub in ch.get("subsections") or []:
                sub_title = sub.get("title") if isinstance(sub, dict) else str(sub)
                if sub_title and sub_title not in draft_content:
                    checks.append(self._issue(
                        check_id="C07_章节完整性",
                        check_name="章节完整性",
                        problem=f"生成稿缺少二级小节：{sub_title}",
                        expected=f"章节「{title}」下应包含小节「{sub_title}」",
                        actual="draft.md 中未找到该小节标题",
                        suggestion=f"在「{title}」中补充「{sub_title}」小节。",
                        requirement_ref=self._first_ref(
                            ch.get("requirement_refs") or ch.get("scoring_refs")
                        ),
                        draft_ref={"path": draft_path, "heading": title or "正文"},
                    ))

        for field_path, check_id, check_name in [
            ("K10_星标项", "C08_星标项覆盖", "星标项覆盖"),
            ("K11_废标条款", "C09_废标条款自查", "废标条款自查"),
        ]:
            for i, (item, page) in enumerate(k_field_items_with_pages(parsed.get(field_path))):
                if not item:
                    continue
                if not self._quote_covered(str(item), draft_content):
                    checks.append(self._issue(
                        check_id=check_id,
                        check_name=check_name,
                        problem=f"未覆盖招标要求：{str(item)[:80]}",
                        expected="标书正文应明确响应该要求",
                        actual="draft.md 中未找到相近表述",
                        suggestion="在对应商务或技术章节中逐条响应，并引用证明材料。",
                        requirement_ref=make_evidence_ref(
                            page=page,
                            quote=str(item),
                            field_path=f"{field_path}.items[{i}]",
                        ),
                        draft_ref={"path": draft_path, "heading": self._nearest_heading(draft_content, str(item))},
                    ))

        placeholders = re.findall(r"\[待补充:[^\]]+\]", draft_content)
        for placeholder in placeholders[:10]:
            checks.append(self._issue(
                check_id="C11_待补充占位",
                check_name="待补充占位检查",
                problem=f"生成稿仍包含占位符：{placeholder}",
                expected="终审稿不应包含待补充占位",
                actual=placeholder,
                suggestion="补齐该占位符对应的真实材料或响应内容。",
                requirement_ref=None,
                draft_ref={"path": draft_path, "heading": self._nearest_heading(draft_content, placeholder)},
            ))

        consistency_fields = [
            ("K01_项目名称", "C01_名称一致性", "项目名称"),
            ("K02_招标编号", "C01_名称一致性", "招标编号"),
            ("K04_预算金额", "C05_金额一致性", "预算金额"),
            ("K05_投标截止时间", "C04_期限一致性", "投标截止时间"),
        ]
        for field_path, check_id, label in consistency_fields:
            expected_value = k_field_value(parsed.get(field_path))
            if expected_value and expected_value != "未找到" and expected_value not in draft_content:
                checks.append(self._issue(
                    check_id=check_id,
                    check_name=label,
                    problem=f"生成稿未出现解析出的{label}",
                    expected=str(expected_value),
                    actual="draft.md 中未找到完全一致文本",
                    suggestion=f"在封面、目录或对应章节中补充并统一{label}。",
                    requirement_ref=self._first_ref(evidence_from_k_field(parsed.get(field_path), field_path)),
                    draft_ref={"path": draft_path, "heading": "项目信息"},
                    severity="warning",
                ))

        k13 = k_field_value(parsed.get("K13_偏离表格式要求"))
        if k13 and "偏离" in k13 and "偏离表" not in draft_content:
            checks.append(self._issue(
                check_id="C12_偏离表完整性",
                check_name="偏离表完整性",
                problem="招标文件要求偏离表，但生成稿未包含偏离表说明",
                expected=k13,
                actual="draft.md 中未找到“偏离表”",
                suggestion="补充商务/技术偏离表，并确认 deviation.md 已生成。",
                requirement_ref=self._first_ref(evidence_from_k_field(parsed.get("K13_偏离表格式要求"), "K13_偏离表格式要求")),
                draft_ref={"path": draft_path, "heading": "附录"},
            ))

        volumes = {ch.get("volume") for ch in outline if ch.get("volume")}
        if (
            "commercial" in volumes
            and "商务文件" not in draft_content
            and "商务标" not in draft_content
        ):
            checks.append(self._issue(
                check_id="C13_分卷一致性",
                check_name="商务/技术分卷一致性",
                problem="提纲包含商务文件章节，但生成稿未显示商务文件分卷",
                expected="生成稿应包含“商务文件”分卷标题",
                actual="draft.md 中未找到“商务文件”",
                suggestion="重新生成主标书，确保分卷目录和正文同步。",
                draft_ref={"path": draft_path, "heading": "目录"},
            ))
        if (
            "technical" in volumes
            and "技术文件" not in draft_content
            and "技术标" not in draft_content
        ):
            checks.append(self._issue(
                check_id="C13_分卷一致性",
                check_name="商务/技术分卷一致性",
                problem="提纲包含技术文件章节，但生成稿未显示技术文件分卷",
                expected="生成稿应包含“技术文件”分卷标题",
                actual="draft.md 中未找到“技术文件”",
                suggestion="重新生成主标书，确保分卷目录和正文同步。",
                draft_ref={"path": draft_path, "heading": "目录"},
            ))

        return checks

    def _merge_deterministic_checks(
        self,
        report: dict[str, Any],
        deterministic_checks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not deterministic_checks:
            report["issues"] = [
                c for c in report.get("checks", [])
                if c.get("status") in ("warning", "fail")
            ]
            return report

        checks = list(report.get("checks") or [])
        by_id = {c.get("check_id"): i for i, c in enumerate(checks)}
        for issue in deterministic_checks:
            check_id = issue.get("check_id")
            if check_id in by_id:
                existing = checks[by_id[check_id]]
                if existing.get("status") == "pass" or issue.get("status") == "fail":
                    checks[by_id[check_id]] = issue
                else:
                    existing["status"] = issue.get("status", existing.get("status"))
                    existing["issue"] = "; ".join(
                        part for part in [existing.get("issue"), issue.get("issue")]
                        if part
                    )
                    existing["problem"] = existing.get("problem") or issue.get("problem")
                    existing["expected"] = existing.get("expected") or issue.get("expected")
                    existing["actual"] = existing.get("actual") or issue.get("actual")
                    existing["suggestion"] = existing.get("suggestion") or issue.get("suggestion")
                    existing["requirement_ref"] = existing.get("requirement_ref") or issue.get("requirement_ref")
                    existing["draft_ref"] = existing.get("draft_ref") or issue.get("draft_ref")
                    existing["blocking"] = existing.get("blocking") or issue.get("blocking")
            else:
                checks.append(issue)

        summary = {
            "high": sum(1 for c in checks if c.get("status") == "fail"),
            "medium": sum(1 for c in checks if c.get("status") == "warning"),
            "low": sum(1 for c in checks if c.get("status") == "pass"),
        }
        report["checks"] = checks
        report["issues"] = [c for c in checks if c.get("status") in ("warning", "fail")]
        report["summary"] = summary
        report["deterministic_count"] = len(deterministic_checks)
        return report

    @staticmethod
    def _issue(
        check_id: str,
        check_name: str,
        problem: str,
        expected: str,
        actual: str,
        suggestion: str,
        requirement_ref: dict[str, Any] | None = None,
        draft_ref: dict[str, Any] | None = None,
        severity: str = "fail",
    ) -> dict[str, Any]:
        return {
            "check_id": check_id,
            "check_name": check_name,
            "status": "fail" if severity == "fail" else "warning",
            "severity": severity,
            "issue": problem,
            "problem": problem,
            "expected": expected,
            "actual": actual,
            "suggestion": suggestion,
            "requirement_ref": requirement_ref,
            "draft_ref": draft_ref,
            "blocking": severity == "fail",
        }

    @staticmethod
    def _quote_covered(quote: str, draft_content: str) -> bool:
        quote = re.sub(r"\s+", "", quote or "")
        if not quote:
            return True
        if quote in re.sub(r"\s+", "", draft_content):
            return True
        keywords = [
            w for w in re.findall(r"[\u4e00-\u9fff]{2,}", quote)
            if w not in {"必须", "应当", "提供", "满足", "要求"}
        ]
        if not keywords:
            return False
        hits = sum(1 for w in keywords[:6] if w in draft_content)
        return hits >= max(1, min(2, len(keywords[:6])))

    @staticmethod
    def _nearest_heading(draft_content: str, needle: str) -> str:
        idx = draft_content.find(needle) if needle else -1
        if idx < 0:
            return "正文"
        headings = [
            (m.start(), m.group(2).strip())
            for m in re.finditer(r"^(#{1,4})\s+(.+)$", draft_content, re.MULTILINE)
        ]
        current = "正文"
        for pos, heading in headings:
            if pos > idx:
                break
            current = heading
        return current

    @staticmethod
    def _display_draft_path(path: str | None) -> str:
        if not path:
            return "main/draft.md"
        p = Path(path)
        if p.parent.name == "main":
            return "main/draft.md"
        return p.name

    @staticmethod
    def _first_ref(refs: Any) -> dict[str, Any] | None:
        if isinstance(refs, list) and refs:
            first = refs[0]
            return first if isinstance(first, dict) else None
        if isinstance(refs, dict):
            return refs
        return None

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
