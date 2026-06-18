"""
测试 ReviewerAgent 固定 schema 输出。

手动运行：
PYTHONPATH=. python3 tests/test_reviewer_agent.py
"""
from agents.reviewer_agent import C01_C10_CHECKS, SUB_BID_EXTRA_CHECKS, ReviewerAgent


def test_reviewer_normalizes_structured_schema():
    agent = ReviewerAgent()
    report = agent._normalize_report(
        {
            "checks": [
                {
                    "check_id": "C01_名称一致性",
                    "check_name": "名称一致性",
                    "status": "pass",
                    "issue": "",
                    "suggestion": "",
                },
                {
                    "check_id": "C02_产品名称一致性",
                    "check_name": "产品名称一致性",
                    "status": "warning",
                    "issue": "产品简称不统一",
                    "suggestion": "统一产品简称",
                },
            ]
        },
        C01_C10_CHECKS,
        "main",
    )

    assert len(report["checks"]) == len(C01_C10_CHECKS)
    assert report["summary"]["medium"] == 9
    assert report["summary"]["low"] == 1
    assert report["summary"]["high"] == 0
    assert report["checks"][1]["issue"] == "产品简称不统一"
    print("✅ test_reviewer_normalizes_structured_schema passed")


def test_reviewer_error_report_uses_fixed_schema():
    report = ReviewerAgent()._error_report("LLM 不可用", "main")
    assert len(report["checks"]) == len(C01_C10_CHECKS)
    assert report["summary"]["high"] == 1
    assert report["summary"]["medium"] == len(C01_C10_CHECKS) - 1
    assert report["error"] == "LLM 不可用"
    print("✅ test_reviewer_error_report_uses_fixed_schema passed")


def test_reviewer_error_report_includes_sub_bid_checks():
    report = ReviewerAgent()._error_report("LLM 不可用", "sub")
    assert len(report["checks"]) == len(C01_C10_CHECKS) + len(SUB_BID_EXTRA_CHECKS)
    assert report["checks"][-1]["check_id"] == "SUB03_内容独立性"
    assert report["summary"]["high"] == 1
    print("✅ test_reviewer_error_report_includes_sub_bid_checks passed")


def test_reviewer_rejects_empty_draft():
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from types import SimpleNamespace

    with TemporaryDirectory() as tmp:
        draft = Path(tmp) / "draft.md"
        draft.write_text("   \n", encoding="utf-8")

        class FakeSession:
            def get(self, model, _id):
                if model.__name__ == "Tender":
                    return SimpleNamespace(id=_id, project_id=1, draft_path=str(draft))
                return None

        import agents.reviewer_agent as reviewer_module

        old_get_session = reviewer_module.get_session
        reviewer_module.get_session = lambda: FakeSession()
        try:
            content, context, error = ReviewerAgent()._load_review_context(
                SimpleNamespace(tender_id=1)
            )
        finally:
            reviewer_module.get_session = old_get_session

        assert content == ""
        assert context == {}
        assert error == "draft.md 为空，无法终审"
        print("✅ test_reviewer_rejects_empty_draft passed")


if __name__ == "__main__":
    print("Running ReviewerAgent tests...\n")
    test_reviewer_normalizes_structured_schema()
    test_reviewer_error_report_uses_fixed_schema()
    test_reviewer_error_report_includes_sub_bid_checks()
    test_reviewer_rejects_empty_draft()
    print("\n🎉 All tests passed!")
