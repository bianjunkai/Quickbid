"""
测试 Orchestrator 主标文件落盘的 review 回归项。

手动运行：
PYTHONPATH=. python3 tests/test_orchestrator_file_writing.py
"""
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

from orchestrator import Orchestrator


def test_sanitize_filename_keeps_r_n_t_letters():
    actual = Orchestrator._sanitize_filename("system integration report_v2")
    assert actual == "system integration report_v2"
    assert Orchestrator._sanitize_filename("a\nb\rc\td") == "a_b_c_d"
    print("✅ test_sanitize_filename_keeps_r_n_t_letters passed")


def test_write_main_tender_files_accepts_non_numeric_chapter_no():
    with TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "project"
        project_dir.mkdir()
        tender_file = project_dir / "tender.pdf"
        tender_file.write_text("fake pdf placeholder", encoding="utf-8")

        project = SimpleNamespace(
            id=1,
            name="测试项目",
            tender_file_path=str(tender_file),
        )
        tender = SimpleNamespace(id=999999)
        gen_result = {
            "content": "# draft",
            "chapters": [
                {
                    "no": "?",
                    "title": "system integration report_v2",
                    "category": "03_技术方案",
                    "content": "chapter body",
                }
            ],
        }

        draft_path = Orchestrator({})._write_main_tender_files(
            project,
            tender,
            gen_result,
            {"K01_项目名称": {"value": "测试项目"}},
        )

        assert draft_path.endswith("main/draft.md")
        assert (project_dir / "main" / "draft.md").exists()
        chapter_path = (
            project_dir
            / "main"
            / "03_技术方案"
            / "00_system integration report_v2.md"
        )
        assert chapter_path.read_text(encoding="utf-8") == "chapter body"
        print("✅ test_write_main_tender_files_accepts_non_numeric_chapter_no passed")


def test_write_sub_tender_files_and_deviation_table():
    with TemporaryDirectory() as tmp:
        project_dir = Path(tmp) / "project"
        project_dir.mkdir()
        tender_file = project_dir / "tender.pdf"
        tender_file.write_text("fake pdf placeholder", encoding="utf-8")

        project = SimpleNamespace(
            id=1,
            name="测试项目",
            tender_file_path=str(tender_file),
        )
        tender = SimpleNamespace(id=999998)
        parsed = {
            "K01_项目名称": {"value": "测试项目"},
            "K08_技术要求": {"value": "支持电子病历集成；支持单点登录"},
            "K09_商务资质要求": {"value": "具备软件企业证书；提供售后服务承诺"},
            "K10_星标项": {"items": ["必须满足数据安全要求"]},
            "K13_偏离表格式要求": {"value": "逐条列明响应情况"},
        }

        draft_path = Orchestrator({})._write_sub_tender_files(
            project,
            tender,
            {"content": "# 测试项目 — 投标文件（陪标）"},
            parsed,
        )

        assert draft_path.endswith("sub/draft.md")
        assert (project_dir / "sub" / "cover.md").exists()
        assert (project_dir / "sub" / "draft.md").exists()
        deviation = (project_dir / "sub" / "deviation.md").read_text(encoding="utf-8")
        assert "商务条款偏离表" in deviation
        assert "技术条款偏离表" in deviation
        assert "支持电子病历集成" in deviation
        assert "占位" not in deviation
        print("✅ test_write_sub_tender_files_and_deviation_table passed")


if __name__ == "__main__":
    print("Running Orchestrator file-writing tests...\n")
    test_sanitize_filename_keeps_r_n_t_letters()
    test_write_main_tender_files_accepts_non_numeric_chapter_no()
    test_write_sub_tender_files_and_deviation_table()
    print("\n🎉 All tests passed!")
