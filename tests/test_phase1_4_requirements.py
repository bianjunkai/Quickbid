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
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

_tmp = TemporaryDirectory()
os.environ["TENDER_DB_PATH"] = os.path.join(_tmp.name, "phase1_4.db")

import main  # noqa: E402
from agents.bid_parser.evidence import evidence_from_k_field, evidence_from_marker_item  # noqa: E402
from agents.bid_parser.pipeline import BidParsePipeline  # noqa: E402
from agents.generator_agent import GeneratorAgent  # noqa: E402
from agents.matcher_agent import MatcherAgent  # noqa: E402
from models import Project, get_session, init_db  # noqa: E402


class DummyLLM:
    is_available = False


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


def test_low_price_review_clause_is_preserved_during_parse_validation():
    pipeline = BidParsePipeline(DummyLLM())
    parsed = {
        "K07_评分标准": {"value": "综合评分法", "source_page": 3},
        "K10_星标项": {"items": [], "source_pages": []},
        "scoring": {"method": "综合评分法"},
        "marker_extractions": {"high_items": []},
    }
    full_text = (
        "[PAGE: 12]\n"
        "投标报价明显低于其他有效投标报价的，评标委员会应启动低价审核，"
        "投标人不能证明其报价合理性的，不作为中标候选人。"
    )
    final = pipeline.step3_validate(parsed, full_text)

    low_price = final["scoring"]["low_price_review"]
    assert low_price["source_page"] == 12
    assert "低价审核" in low_price["trigger"]
    assert "低价审核" in final["K07_评分标准"]["value"]
    assert any("低价审核" in item for item in final["K10_星标项"]["items"])
    assert final["marker_extractions"]["high_items"][0]["source_page"] == 12

    parsed_with_nulls = {
        "K07_评分标准": {"value": "综合评分法", "source_page": 3},
        "K10_星标项": {"items": [], "source_pages": []},
        "scoring": None,
        "marker_extractions": None,
    }
    final_with_nulls = pipeline.step3_validate(parsed_with_nulls, full_text)
    assert final_with_nulls["scoring"]["low_price_review"]["source_page"] == 12
    assert final_with_nulls["marker_extractions"]["high_items"][0]["source_page"] == 12
    print("✅ test_low_price_review_clause_is_preserved_during_parse_validation passed")


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


def test_natural_language_correction_generates_patch_proposal():
    patches = main._extract_parsed_data_patch_proposals("预算应为 900 万，招标编号改为 ZB-2026-01")
    by_path = {p.field_path: p for p in patches}
    assert set(by_path) == {"K04_预算金额", "K02_招标编号"}
    assert by_path["K04_预算金额"].value == "900 万"
    assert by_path["K04_预算金额"].source == "chat_nl"
    assert by_path["K02_招标编号"].value == "ZB-2026-01"
    print("✅ test_natural_language_correction_generates_patch_proposal passed")


def test_natural_language_page_correction_generates_source_page_patch():
    parsed = {
        "K08_技术要求": {"value": "支持单点登录", "source_page": 8},
        "K10_星标项": {"items": ["必须满足安全要求", "必须提供承诺函"], "source_pages": [3, 4]},
    }
    patches = main._extract_parsed_data_patch_proposals(
        "技术要求来源页是第 23 页，星标项在第 12 页",
        parsed,
    )
    by_path = {p.field_path: p for p in patches}
    assert by_path["K08_技术要求.source_page"].value == 23
    assert by_path["K10_星标项.source_pages"].value == [12, 12]
    assert by_path["K08_技术要求.source_page"].source == "chat_nl_page"
    print("✅ test_natural_language_page_correction_generates_source_page_patch passed")


def test_price_calculator_scores_and_low_price_risk():
    parsed = {
        "K04_预算金额": {"value": "900万", "source_page": 1},
        "K07_评分标准": {"value": "价格分30分，价格分=最低报价/投标报价×30"},
        "scoring": {
            "price_ratio": 30,
            "low_price_review": {"trigger": "投标报价低于最高限价80%时启动异常低价审核"},
        },
    }
    result = main._calculate_price_scores(
        parsed,
        lowest_price=700,
        main_price=760,
        competitor_price=780,
    )

    assert result["ok"] is True
    assert result["price_score_max"] == 30
    assert result["low_price_ratio_display"] == "80.00%"
    assert result["low_price_threshold"] == 720
    by_key = {row["key"]: row for row in result["rows"]}
    assert by_key["lowest"]["score"] == 30
    assert round(by_key["main"]["score"], 4) == round(30 * 700 / 760, 4)
    assert by_key["lowest"]["triggers_low_price"] is True
    assert by_key["main"]["triggers_low_price"] is False
    print("✅ test_price_calculator_scores_and_low_price_risk passed")


def test_chat_price_calculator_emits_tool_result():
    project_id = _create_project({
        "K04_预算金额": {"value": "900万", "source_page": 1},
        "scoring": {
            "price_ratio": 30,
            "low_price_review": {"trigger": "低于最高限价80%触发异常低价审核"},
        },
    })

    async def collect():
        events = []
        async for ev in main._run_chat_sse(
            project_id,
            "价格测算：最低报价700万，主标报价760万，对手报价780万",
        ):
            events.append(main.json.loads(ev["data"]))
        return events

    events = asyncio.run(collect())
    tool_call_id = next(
        ev["toolCallId"] for ev in events
        if ev.get("type") == "tool-input-available"
        and ev.get("toolName") == "priceCalculator"
    )
    tool_outputs = [
        ev for ev in events
        if ev.get("type") == "tool-output-available"
        and ev.get("toolCallId") == tool_call_id
    ]
    assert tool_outputs
    output = tool_outputs[-1]["output"]
    assert output["ok"] is True
    assert output["any_low_price_risk"] is True
    assert output["rows"][1]["label"] == "主标报价"
    print("✅ test_chat_price_calculator_emits_tool_result passed")


def test_chat_correction_updates_parsed_data_and_returns_parser_report_payload():
    project_id = _create_project({
        "K04_预算金额": {"value": "800万", "source_page": 5},
    })

    async def collect():
        events = []
        async for ev in main._run_chat_sse(project_id, "预算应为 900 万"):
            events.append(main.json.loads(ev["data"]))
        return events

    events = asyncio.run(collect())
    tool_outputs = [
        ev["output"] for ev in events
        if ev.get("type") == "tool-output-available"
    ]
    assert tool_outputs
    output = tool_outputs[-1]
    assert output["K04_预算金额"]["value"] == "900 万"
    assert output["_correction_applied"][0]["field_path"] == "K04_预算金额"
    assert output["_corrections"][0]["source"] == "chat_nl"

    session = get_session()
    project = session.get(Project, project_id)
    parsed = main.json.loads(project.parsed_data)
    assert parsed["K04_预算金额"]["value"] == "900 万"
    assert parsed["_corrections"][0]["new_value"] == "900 万"
    assert project.budget == 900
    print("✅ test_chat_correction_updates_parsed_data_and_returns_parser_report_payload passed")


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
    assert MatcherAgent._infer_volume("开标一览表", "05_商务文件") == "commercial"
    print("✅ test_matcher_outline_volume_and_refs passed")


def test_matcher_applies_tender_template_requirements_to_outline():
    parsed = {
        "K12_章节模板要求": {
            "value": "投标文件应包括：投标函、开标一览表、分项报价表、技术条款偏离表、实施方案",
            "source_page": 9,
        },
        "templates": {
            "bid_doc_structure": [
                {"section_no": "一", "name": "资格证明文件", "source_page": 10},
                {"section_no": "二", "name": "技术方案", "source_page": 11},
            ]
        },
    }
    outline = MatcherAgent._normalize_outline([
        {
            "id": "ch1",
            "title": "商务响应文件",
            "category": "05_商务文件",
            "volume": "commercial",
            "source": "k12",
        },
        {
            "id": "ch2",
            "title": "技术响应文件",
            "category": "03_技术方案",
            "volume": "technical",
            "source": "k12",
        },
    ])
    enriched = MatcherAgent._apply_template_requirements(outline, parsed)
    commercial_titles = [
        sub["title"]
        for ch in enriched if ch["volume"] == "commercial"
        for sub in ch.get("subsections", [])
    ]
    technical_titles = [
        sub["title"]
        for ch in enriched if ch["volume"] == "technical"
        for sub in ch.get("subsections", [])
    ]
    chapter_titles = [ch["title"] for ch in enriched]
    assert "资格证明文件" in chapter_titles
    assert "技术方案" in chapter_titles
    assert "投标函" in commercial_titles
    assert "开标一览表" in commercial_titles
    assert "分项报价表" in commercial_titles
    assert "技术条款偏离表" in technical_titles
    print("✅ test_matcher_applies_tender_template_requirements_to_outline passed")


def test_generator_assembled_markdown_groups_by_volume():
    markdown = GeneratorAgent()._assemble_markdown(
        "测试项目",
        [
            {
                "no": 1,
                "title": "资格证明文件",
                "volume": "commercial",
                "content": "## 第1章 资格证明文件\n商务内容",
            },
            {
                "no": 2,
                "title": "技术方案",
                "volume": "technical",
                "content": "## 第1章 技术方案\n技术内容",
            },
        ],
        {"K01_项目名称": {"value": "测试项目"}},
    )
    assert "### 商务文件" in markdown
    assert "### 技术文件" in markdown
    assert "## 商务文件" in markdown
    assert "## 技术文件" in markdown
    assert markdown.index("### 商务文件") < markdown.index("### 技术文件")
    assert "- 第1章 资格证明文件" in markdown
    assert "- 第1章 技术方案" in markdown
    assert "- 第2章 技术方案" not in markdown
    print("✅ test_generator_assembled_markdown_groups_by_volume passed")


def test_export_outline_markdown_contains_two_level_catalog_and_refs():
    project_id = _create_project({
        "_confirmed_outline": [
            {
                "id": "ch1",
                "no": 1,
                "title": "资格证明文件",
                "volume": "commercial",
                "category": "01_公司资质",
                "source": "template",
                "subsections": [{"id": "ch1.1", "title": "投标函"}],
                "requirement_refs": [
                    {"page": 8, "quote": "投标函格式", "label": "投标函"}
                ],
            },
            {
                "id": "ch2",
                "no": 2,
                "title": "技术方案",
                "volume": "technical",
                "category": "03_技术方案",
                "source": "scoring",
                "subsections": [{"id": "ch2.1", "title": "系统架构"}],
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
        assert "### 商务文件" in text
        assert "### 技术文件" in text
        assert "1. **资格证明文件**" in text
        assert "1. **技术方案**" in text
        assert "2. **技术方案**" not in text
        assert "系统架构" in text
        assert "P.8" in text
        assert "P.20" in text
        assert result["download_url"] == f"/api/downloads/outlines/{project_id}/markdown"
    finally:
        main.EXPORTS_DIR = old_exports_dir
    print("✅ test_export_outline_markdown_contains_two_level_catalog_and_refs passed")


def test_outline_ref_format_does_not_expose_internal_field_path():
    text = main._format_outline_refs([
        {
            "page": None,
            "quote": "系统架构；5；架构清晰",
            "field_path": "scoring.dimensions[0].sub_items[0]",
            "label": "系统架构；5",
        }
    ])
    assert "系统架构" in text
    assert "scoring.dimensions" not in text
    print("✅ test_outline_ref_format_does_not_expose_internal_field_path passed")


if __name__ == "__main__":
    print("Running Phase 1-4 requirement tests...\n")
    test_evidence_helpers_adapt_existing_shapes()
    test_low_price_review_clause_is_preserved_during_parse_validation()
    test_patch_parsed_data_records_correction_audit()
    test_natural_language_correction_generates_patch_proposal()
    test_natural_language_page_correction_generates_source_page_patch()
    test_price_calculator_scores_and_low_price_risk()
    test_chat_price_calculator_emits_tool_result()
    test_chat_correction_updates_parsed_data_and_returns_parser_report_payload()
    test_matcher_outline_volume_and_refs()
    test_matcher_applies_tender_template_requirements_to_outline()
    test_generator_assembled_markdown_groups_by_volume()
    test_export_outline_markdown_contains_two_level_catalog_and_refs()
    test_outline_ref_format_does_not_expose_internal_field_path()
    print("\n🎉 All tests passed!")
