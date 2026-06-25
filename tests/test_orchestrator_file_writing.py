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
            / "technical"
            / "03_技术方案"
            / "01_system integration report_v2.md"
        )
        assert chapter_path.read_text(encoding="utf-8") == "chapter body"
        cover = (project_dir / "main" / "cover.md").read_text(encoding="utf-8")
        assert "[技术文件] 第1章 system integration report_v2" in cover
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
        assert "医院信息化系统建设技术要求" not in deviation
        assert "商务资质、授权、服务承诺等商务条款" not in deviation
        assert "占位" not in deviation
        print("✅ test_write_sub_tender_files_and_deviation_table passed")


def test_deviation_table_expands_structured_requirements_line_by_line():
    parsed = {
        "K01_项目名称": {"value": "测试项目"},
        "K13_偏离表格式要求": {"value": "技术和商务偏离表应逐条响应"},
        "qualification": {
            "requirements": [
                {
                    "id": "Q1",
                    "type": "资质",
                    "name": "具备有效营业执照",
                    "proof_type": "营业执照复印件",
                    "is_mandatory": True,
                },
                {
                    "id": "Q2",
                    "type": "业绩",
                    "name": "近三年类似项目业绩",
                    "proof_type": "合同证明",
                    "is_mandatory": True,
                },
            ]
        },
        "commercial": {
            "payment": "按合同约定分期付款",
            "warranty": "三年免费质保",
        },
        "tech": {
            "functional_requirements": [
                {
                    "module": "集成",
                    "name": "电子病历集成",
                    "description": "支持与医院电子病历系统对接",
                    "priority": "HIGH",
                },
                {
                    "module": "认证",
                    "name": "单点登录",
                    "description": "支持统一身份认证",
                    "priority": "HIGH",
                },
            ],
            "non_functional_requirements": {
                "performance": "并发用户数不少于 500",
            },
            "security_requirements": {
                "level": "等保三级",
                "items": ["敏感数据加密存储", "访问日志留存不少于 180 天"],
            },
            "deliverables": ["部署方案", "验收报告"],
        },
    }

    deviation = Orchestrator({})._build_deviation_markdown(parsed, tender_type="main")

    for expected in [
        "具备有效营业执照",
        "近三年类似项目业绩",
        "按合同约定分期付款",
        "三年免费质保",
        "电子病历集成",
        "单点登录",
        "并发用户数不少于 500",
        "等保三级",
        "敏感数据加密存储",
        "访问日志留存不少于 180 天",
        "部署方案",
        "验收报告",
    ]:
        assert expected in deviation
    assert "医院信息化系统建设技术要求" not in deviation
    assert "商务资质、授权、服务承诺等商务条款" not in deviation
    print("✅ test_deviation_table_expands_structured_requirements_line_by_line passed")


def test_deviation_confirmation_preview_is_written_to_markdown():
    orch = Orchestrator({})
    orch.ctx.parsed_data = {
        "K01_项目名称": {"value": "测试项目"},
        "K08_技术要求": {"value": "支持电子病历集成"},
        "K09_商务资质要求": {"value": "具备有效营业执照"},
    }

    result = orch._start_deviation_confirmation()
    preview = result["deviation_preview"]
    assert "具备有效营业执照" in preview["business_items"]
    assert "支持电子病历集成" in preview["technical_items"]

    assert orch._apply_deviation_message("补充技术偏离：支持历史数据迁移；提供接口文档")
    orch._confirm_deviation_items()
    confirmed = orch.ctx.parsed_data["_confirmed_deviation_items"]
    assert "支持历史数据迁移" in confirmed["technical"]
    assert "提供接口文档" in confirmed["technical"]

    deviation = orch._build_deviation_markdown(orch.ctx.parsed_data, tender_type="main")
    assert "支持历史数据迁移" in deviation
    assert "提供接口文档" in deviation
    print("✅ test_deviation_confirmation_preview_is_written_to_markdown passed")


if __name__ == "__main__":
    print("Running Orchestrator file-writing tests...\n")
    test_sanitize_filename_keeps_r_n_t_letters()
    test_write_main_tender_files_accepts_non_numeric_chapter_no()
    test_write_sub_tender_files_and_deviation_table()
    test_deviation_table_expands_structured_requirements_line_by_line()
    test_deviation_confirmation_preview_is_written_to_markdown()
    print("\n🎉 All tests passed!")
