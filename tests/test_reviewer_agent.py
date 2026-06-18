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


if __name__ == "__main__":
    print("Running ReviewerAgent tests...\n")
    test_reviewer_normalizes_structured_schema()
    test_reviewer_error_report_uses_fixed_schema()
    test_reviewer_error_report_includes_sub_bid_checks()
    print("\n🎉 All tests passed!")
