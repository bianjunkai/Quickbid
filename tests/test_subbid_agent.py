"""
测试 SubBidAgent 的 Phase 4 生成路径。

手动运行：
PYTHONPATH=. python3 tests/test_subbid_agent.py
"""
from agents.base import AgentContext
from agents.subbid_agent import SubBidAgent


class FakeAvailableClient:
    is_available = True

    def chat(self, messages, temperature=0.0, max_tokens=4096):
        assert "主标 Markdown" in messages[-1]["content"]
        return "# 测试项目 — 投标文件（陪标）\n\n## 商务资质\n\n完全响应。"


class FakeUnavailableClient:
    is_available = False


def test_subbid_fails_without_main_tender_context():
    ctx = AgentContext(project_id=1, parsed_data={"K01_项目名称": {"value": "测试项目"}})
    result = SubBidAgent().execute(ctx)

    assert result["failed"] is True
    assert "缺少主标 tender_id" in result["errors"][0]
    print("✅ test_subbid_fails_without_main_tender_context passed")


def test_subbid_uses_llm_when_main_draft_is_available(monkeypatch=None):
    import agents.subbid_agent as subbid_module

    old_client = subbid_module.BidLLMClient
    subbid_module.BidLLMClient = lambda: FakeAvailableClient()
    try:
        ctx = AgentContext(
            project_id=1,
            tender_id=1,
            parsed_data={"K01_项目名称": {"value": "测试项目"}},
            draft_content="# 测试项目 — 投标文件（主标）\n\n## 商务资质\n\n资质内容。",
        )
        result = SubBidAgent().execute(ctx)

        assert result["tender_type"] == "sub"
        assert result["errors"] == []
        assert "投标文件（陪标）" in result["content"]
        assert ctx.sub_draft_content == result["content"]
        print("✅ test_subbid_uses_llm_when_main_draft_is_available passed")
    finally:
        subbid_module.BidLLMClient = old_client


def test_subbid_reports_missing_llm_key(monkeypatch=None):
    import agents.subbid_agent as subbid_module

    old_client = subbid_module.BidLLMClient
    subbid_module.BidLLMClient = lambda: FakeUnavailableClient()
    try:
        ctx = AgentContext(
            project_id=1,
            tender_id=1,
            parsed_data={"K01_项目名称": {"value": "测试项目"}},
            draft_content="# 主标",
        )
        result = SubBidAgent().execute(ctx)

        assert result["failed"] is True
        assert "LLM 不可用" in result["errors"][0]
        print("✅ test_subbid_reports_missing_llm_key passed")
    finally:
        subbid_module.BidLLMClient = old_client


if __name__ == "__main__":
    print("Running SubBidAgent tests...\n")
    test_subbid_fails_without_main_tender_context()
    test_subbid_uses_llm_when_main_draft_is_available()
    test_subbid_reports_missing_llm_key()
    print("\n🎉 All tests passed!")
