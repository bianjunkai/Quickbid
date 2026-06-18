"""
测试主标 Markdown / Word 导出。

手动运行：
PYTHONPATH=. python3 tests/test_export_tender.py
"""
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import main
from fastapi import HTTPException


def test_export_markdown_and_word_from_draft_path():
    with TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        draft_path = tmp_dir / "project" / "main" / "draft.md"
        draft_path.parent.mkdir(parents=True)
        draft_path.write_text(
            "# 测试项目\n\n## 技术方案\n\n- 平台能力\n\n正文内容",
            encoding="utf-8",
        )

        old_exports_dir = main.EXPORTS_DIR
        main.EXPORTS_DIR = tmp_dir / "exports"
        try:
            tender = SimpleNamespace(id=42, draft_path=str(draft_path))

            markdown = main._export_tender_file(tender, "markdown")
            markdown_path = Path(markdown["export_path"])
            assert markdown["format"] == "markdown"
            assert markdown["download_url"] == "/api/downloads/42/markdown"
            assert markdown_path.exists()
            assert markdown_path.read_text(encoding="utf-8") == draft_path.read_text(encoding="utf-8")

            word = main._export_tender_file(tender, "word")
            word_path = Path(word["export_path"])
            assert word["format"] == "word"
            assert word["download_url"] == "/api/downloads/42/word"
            assert word_path.exists()
            assert word_path.suffix == ".docx"
            with ZipFile(word_path) as zf:
                assert "word/document.xml" in zf.namelist()

            try:
                main._export_tender_file(tender, "pdf")
            except HTTPException as e:
                assert e.status_code == 400
                assert "PDF 导出暂不支持" in e.detail
            else:
                raise AssertionError("PDF export should be rejected")
        finally:
            main.EXPORTS_DIR = old_exports_dir

    print("✅ test_export_markdown_and_word_from_draft_path passed")


def test_export_format_from_chat_message_keeps_pdf():
    assert main._export_format_from_message("导出PDF") == "pdf"
    assert main._export_format_from_message("导出Word") == "word"
    assert main._export_format_from_message("下载") == "markdown"
    print("✅ test_export_format_from_chat_message_keeps_pdf passed")


if __name__ == "__main__":
    print("Running tender export tests...\n")
    test_export_markdown_and_word_from_draft_path()
    test_export_format_from_chat_message_keeps_pdf()
    print("\n🎉 All tests passed!")
