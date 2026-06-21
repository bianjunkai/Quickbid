"""
测试 Phase 1-4 的基础能力：
- EvidenceRef 兼容层
- parsed_data 显式修正与审计
- outline volume / evidence refs
- outline markdown 导出

手动运行：
PYTHONPATH=. .venv/bin/python tests/test_phase1_4_requirements.py
"""
import os
from pathlib import Path
from tempfile import TemporaryDirectory

_tmp = TemporaryDirectory()
os.environ["TENDER_DB_PATH"] = os.path.join(_tmp.name, "phase1_4.db")

import main  # noqa: E402
from agents.bid_parser.evidence import evidence_from_k_field, evidence_from_marker_item  # noqa: E402
from agents.matcher_agent import MatcherAgent  # noqa: E402
from models import Project, get_session, init_db  # noqa: E402


def _create_project(parsed_data: dict) -> int:
    init_db()
    session = get_session()
    tender_path = Path(_tmp.name) / "project" / "tender.pdf"
    tender_path.parent.mkdir(parents=True, exist_ok=True)
    tender_path.write_text("placeholder", encoding="utf-8")
    project = Project(
        name="测试项目",
        tender_file_path=str(tender_path),
        status="parsed",
        parsed_data=main.json.dumps(parsed_data, ensure_ascii=False),
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project.id


def test_evidence_helpers_adapt_existing_shapes():
    refs = evidence_from_k_field(
        {"value": "预算900万", "source_page": 12},
        "K04_预算金额",
    )
    assert refs[0]["page"] == 12
    assert refs[0]["quote"] == "预算900万"
    assert refs[0]["field_path"] == "K04_预算金额"

    marker_refs = evidence_from_marker_item(
        {"raw_text": "★ 必须满足", "source_page": 8},
        "marker_extractions.fatal_items[0]",
    )
    assert marker_refs[0]["page"] == 8
    assert "必须满足" in marker_refs[0]["quote"]
    print("✅ test_evidence_helpers_adapt_existing_shapes passed")


def test_patch_parsed_data_records_correction_audit():
    project_id = _create_project({
        "K04_预算金额": {"value": "800万", "source_page": 5},
        "scoring": {"dimensions": [{"name": "技术", "max_score": 30}]},
    })

    result = main.patch_parsed_data(
        project_id,
        main.ParsedDataPatchRequest(
            patches=[
                main.ParsedDataPatchItem(
                    field_path="K04_预算金额",
                    value="900万",
                    note="用户确认预算",
                ),
                main.ParsedDataPatchItem(
                    field_path="scoring.dimensions[0].max_score",
                    value=35,
                    source="manual-test",
                ),
            ]
        ),
    )

    parsed = result["parsed_data"]
    assert parsed["K04_预算金额"]["value"] == "900万"
    assert parsed["K04_预算金额"]["source_page"] == 5
    assert parsed["scoring"]["dimensions"][0]["max_score"] == 35
    assert len(parsed["_corrections"]) == 2
    assert parsed["_corrections"][0]["old_value"]["value"] == "800万"
    print("✅ test_patch_parsed_data_records_correction_audit passed")


def test_matcher_outline_volume_and_refs():
    parsed = {
        "K07_评分标准": {"value": "技术方案 30 分", "source_page": 20},
        "K12_章节模板要求": {"value": "投标文件包括商务文件和技术方案", "source_page": 10},
        "scoring": {
            "dimensions": [
                {
                    "name": "技术评分",
                    "source_page": 20,
                    "sub_items": [
                        {"name": "系统架构", "score": 5, "criteria": "架构清晰"}
                    ],
                }
            ]
        },
    }
    outline = MatcherAgent._normalize_outline([
        {
            "id": "ch1",
            "title": "技术方案",
            "category": "03_技术方案",
            "source": "scoring",
            "subsections": [{"title": "系统架构"}],
        },
        {
            "id": "ch2",
            "title": "商务文件",
            "category": "05_商务文件",
            "source": "k12",
        },
    ])
    enriched = MatcherAgent._attach_outline_refs(outline, parsed)
    assert enriched[0]["volume"] == "technical"
    assert enriched[0]["scoring_refs"][0]["page"] == 20
    assert enriched[1]["volume"] == "commercial"
    assert enriched[1]["requirement_refs"][0]["page"] == 10
    print("✅ test_matcher_outline_volume_and_refs passed")


def test_export_outline_markdown_contains_two_level_catalog_and_refs():
    project_id = _create_project({
        "_confirmed_outline": [
            {
                "id": "ch1",
                "no": 1,
                "title": "技术方案",
                "volume": "technical",
                "category": "03_技术方案",
                "source": "scoring",
                "subsections": [{"id": "ch1.1", "title": "系统架构"}],
                "scoring_refs": [
                    {"page": 20, "quote": "系统架构 5 分", "field_path": "scoring.dimensions[0]"}
                ],
            }
        ]
    })
    session = get_session()
    project = session.get(Project, project_id)

    old_exports_dir = main.EXPORTS_DIR
    main.EXPORTS_DIR = Path(_tmp.name) / "exports"
    try:
        result = main._export_outline_file(project, "markdown")
        text = Path(result["export_path"]).read_text(encoding="utf-8")
        assert "## 两级目录" in text
        assert "### 技术标" in text
        assert "系统架构" in text
        assert "P.20" in text
        assert result["download_url"] == f"/api/downloads/outlines/{project_id}/markdown"
    finally:
        main.EXPORTS_DIR = old_exports_dir
    print("✅ test_export_outline_markdown_contains_two_level_catalog_and_refs passed")


if __name__ == "__main__":
    print("Running Phase 1-4 requirement tests...\n")
    test_evidence_helpers_adapt_existing_shapes()
    test_patch_parsed_data_records_correction_audit()
    test_matcher_outline_volume_and_refs()
    test_export_outline_markdown_contains_two_level_catalog_and_refs()
    print("\n🎉 All tests passed!")
