"""
测试聊天入口对“开始解析招标文件”的自然语言识别。

手动运行：
PYTHONPATH=. python3 tests/test_chat_parse_intent.py
"""
import main


def test_parse_intent_accepts_natural_language_when_project_is_parsing():
    assert main._should_start_parse_from_message("开始解析招标文件", "parsing")
    assert main._should_start_parse_from_message("文件已经上传好了，请帮我分析一下", "parsing")
    assert main._should_start_parse_from_message("附件传完了，继续处理", "parsing")
    assert main._should_start_parse_from_message("放好了", "parsing")
    print("✅ test_parse_intent_accepts_natural_language_when_project_is_parsing passed")


def test_parse_intent_avoids_accidental_reparse_after_parsed():
    assert not main._should_start_parse_from_message("解析报告里的预算不对", "parsed")
    assert not main._should_start_parse_from_message("文件里这个字段帮我看看", "generated")
    assert main._should_start_parse_from_message("重新解析招标文件", "parsed")
    print("✅ test_parse_intent_avoids_accidental_reparse_after_parsed passed")


if __name__ == "__main__":
    print("Running chat parse-intent tests...\n")
    test_parse_intent_accepts_natural_language_when_project_is_parsing()
    test_parse_intent_avoids_accidental_reparse_after_parsed()
    print("\n🎉 All tests passed!")
