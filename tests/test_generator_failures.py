"""
测试 GeneratorAgent 失败/中止状态。

手动运行：
PYTHONPATH=. python3 tests/test_generator_failures.py
"""
from agents.base import AgentContext
from agents.generator_agent import GeneratorAgent


class FakeAvailableClient:
    is_available = True


def test_empty_outline_is_failed():
    ctx = AgentContext()
    result = GeneratorAgent().execute(ctx)

    assert result["failed"] is True
    assert result["errors"] == ["提纲为空"]
    print("✅ test_empty_outline_is_failed passed")


def test_consecutive_chapter_failures_abort_generation():
    import agents.generator_agent as generator_module

    class FailingGenerator(GeneratorAgent):
        def _generate_chapter(self, **kwargs):
            raise RuntimeError("boom")

    old_client = generator_module.BidLLMClient
    generator_module.BidLLMClient = lambda: FakeAvailableClient()
    try:
        ctx = AgentContext(
            parsed_data={"K01_项目名称": {"value": "测试项目"}},
            outline=[
                {"id": "ch1", "no": 1, "title": "第一章"},
                {"id": "ch2", "no": 2, "title": "第二章"},
                {"id": "ch3", "no": 3, "title": "第三章"},
                {"id": "ch4", "no": 4, "title": "第四章"},
            ],
        )
        result = FailingGenerator().execute(ctx)

        assert result["failed"] is True
        assert result["aborted"] is True
        assert len(result["errors"]) == 3
        assert result["chapters_count"] == 2
        assert "连续 3 章生成失败" in (ctx.error or "")
        print("✅ test_consecutive_chapter_failures_abort_generation passed")
    finally:
        generator_module.BidLLMClient = old_client


if __name__ == "__main__":
    print("Running GeneratorAgent failure tests...\n")
    test_empty_outline_is_failed()
    test_consecutive_chapter_failures_abort_generation()
    print("\n🎉 All tests passed!")
