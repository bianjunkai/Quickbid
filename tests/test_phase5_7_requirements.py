"""
测试 Phase 5-7 的基础能力：
- 多来源匹配 matched_sources
- Generator 消费招标模板/要求/评分来源
- 工具 readiness 前置检查
- 终审 deterministic issue 定位

手动运行：
PYTHONPATH=. .venv/bin/python tests/test_phase5_7_requirements.py
"""
import os
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

_tmp = TemporaryDirectory()
os.environ["TENDER_DB_PATH"] = os.path.join(_tmp.name, "phase5_7.db")

import main  # noqa: E402
from agents.base import AgentContext  # noqa: E402
from agents.generator_agent import GeneratorAgent  # noqa: E402
from agents.matcher_agent import MatcherAgent  # noqa: E402
from agents.reviewer_agent import ReviewerAgent  # noqa: E402
from models import Project, Tender, get_session, init_db  # noqa: E402


def _create_project(parsed_data: dict, status: str = "parsed") -> int:
    init_db()
    tender_path = Path(_tmp.name) / "project" / "tender.pdf"
    tender_path.parent.mkdir(parents=True, exist_ok=True)
    tender_path.write_text("placeholder", encoding="utf-8")
    session = get_session()
    project = Project(
        name="测试项目",
        tender_file_path=str(tender_path),
        status=status,
        parsed_data=main.json.dumps(parsed_data, ensure_ascii=False),
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project.id


def test_matcher_returns_tender_requirement_sources():
    parsed = {
        "K10_星标项": {"items": ["必须提供安全承诺"], "source_pages": [8]},
        "K12_章节模板要求": {"value": "投标文件应包括商务文件和技术方案", "source_page": 6},
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
    ctx = AgentContext(project_id=1, parsed_data=parsed)
    ctx.outline = [
        {
            "id": "ch1",
            "no": 1,
            "title": "技术方案",
            "volume": "technical",
            "category": "03_技术方案",
            "source": "scoring",
        },
        {
            "id": "ch2",
            "no": 2,
            "title": "商务文件",
            "volume": "commercial",
            "category": "05_商务文件",
            "source": "k12",
        },
    ]

    result = MatcherAgent().match_materials(ctx)
    technical_sources = result["chapters"][0]["matched_sources"]
    commercial_sources = result["chapters"][1]["matched_sources"]
    assert any(s["source_type"] == "scoring_requirement" for s in technical_sources)
    assert any(s["source_type"] == "tender_requirement" for s in commercial_sources)
    assert any(s["source_type"] == "tender_template" for s in commercial_sources)
    scoring_source = next(s for s in technical_sources if s["source_type"] == "scoring_requirement")
    assert scoring_source["evidence"][0]["field_path"]
    print("✅ test_matcher_returns_tender_requirement_sources passed")


def test_generator_formats_matched_requirement_sources():
    block = GeneratorAgent()._format_matched_requirements({
        "matched_sources": [
            {
                "source_type": "material_library",
                "title": "技术方案模板",
                "file_path": "materials/03_技术方案.md",
            },
            {
                "source_type": "scoring_requirement",
                "title": "系统架构",
                "evidence": [
                    {
                        "page": 20,
                        "quote": "系统架构 5 分，架构清晰",
                        "field_path": "scoring.dimensions[0].sub_items[0]",
                    }
                ],
            },
        ]
    })
    assert "material_library" not in block
    assert "[scoring_requirement] 系统架构" in block
    assert "P.20" in block
    assert "系统架构 5 分" in block
    print("✅ test_generator_formats_matched_requirement_sources passed")


def test_tool_readiness_reports_missing_and_ready_states():
    project_id = _create_project({"K01_项目名称": {"value": "测试项目"}})
    session = get_session()
    project = session.get(Project, project_id)

    missing_outline = main._check_tool_readiness(project, "matchMaterials", session)
    assert not missing_outline["ok"]
    assert missing_outline["missing"] == ["outline"]
    assert missing_outline["recoverable_action"] == "请先生成并确认提纲"

    parsed = main.json.loads(project.parsed_data)
    parsed["_confirmed_outline"] = [{"id": "ch1", "title": "技术方案"}]
    parsed["chapters"] = [{"chapter_id": "ch1", "matched_sources": []}]
    project.parsed_data = main.json.dumps(parsed, ensure_ascii=False)
    session.commit()

    ready = main._check_tool_readiness(project, "generateTender", session)
    assert ready["ok"]
    assert ready["missing"] == []
    print("✅ test_tool_readiness_reports_missing_and_ready_states passed")


def test_chat_review_uses_readiness_before_running_tool():
    project_id = _create_project({"K01_项目名称": {"value": "测试项目"}})

    async def collect():
        events = []
        async for ev in main._run_chat_sse(project_id, "终审"):
            events.append(main.json.loads(ev["data"]))
        return events

    events = asyncio.run(collect())
    outputs = [
        ev["output"] for ev in events
        if ev.get("type") == "tool-output-available"
    ]
    assert outputs
    assert outputs[-1]["error"] == "readiness_failed"
    assert outputs[-1]["missing"] == ["draft"]
    assert outputs[-1]["recoverable_action"] == "请先生成主标书"
    print("✅ test_chat_review_uses_readiness_before_running_tool passed")


def test_reviewer_deterministic_checks_include_locations():
    parsed = {
        "K01_项目名称": {"value": "测试项目", "source_page": 1},
        "K04_预算金额": {"value": "900万", "source_page": 2},
        "K10_星标项": {"items": ["必须提供安全承诺"], "source_pages": [8]},
        "_confirmed_outline": [
            {
                "id": "ch1",
                "no": 1,
                "title": "技术方案",
                "volume": "technical",
                "category": "03_技术方案",
                "subsections": [{"title": "数据迁移"}],
                "scoring_refs": [
                    {"page": 20, "quote": "数据迁移 3 分", "field_path": "scoring.dimensions[0]"}
                ],
            }
        ],
    }
    draft = "# 测试项目 — 投标文件\n\n## 技术标\n\n## 第1章 技术方案\n\n[待补充:安全承诺]\n"
    checks = ReviewerAgent()._run_deterministic_checks(
        draft_content=draft,
        project_context={
            "parsed_data": parsed,
            "_draft_path": str(Path(_tmp.name) / "project" / "main" / "draft.md"),
        },
        tender_type="main",
    )
    by_id = {c["check_id"]: c for c in checks}
    assert "C08_星标项覆盖" in by_id
    assert by_id["C08_星标项覆盖"]["requirement_ref"]["page"] == 8
    assert by_id["C08_星标项覆盖"]["draft_ref"]["path"] == "main/draft.md"
    assert "C11_待补充占位" in by_id
    assert "C05_金额一致性" in by_id
    assert by_id["C05_金额一致性"]["status"] == "warning"
    print("✅ test_reviewer_deterministic_checks_include_locations passed")


def test_reviewer_execute_merges_deterministic_checks_when_llm_unavailable():
    project_id = _create_project({
        "K10_星标项": {"items": ["必须提供安全承诺"], "source_pages": [8]},
    }, status="generated")
    draft_path = Path(_tmp.name) / "project" / "main" / "draft.md"
    draft_path.parent.mkdir(parents=True, exist_ok=True)
    draft_path.write_text("# 测试项目\n\n正文未响应要求", encoding="utf-8")

    session = get_session()
    tender = Tender(
        project_id=project_id,
        type="main",
        status="generated",
        draft_path=str(draft_path),
    )
    session.add(tender)
    session.commit()
    session.refresh(tender)

    report = ReviewerAgent().execute(AgentContext(
        project_id=project_id,
        tender_id=tender.id,
        tender_type="main",
    ))
    assert report["error"]
    assert report["deterministic_count"] >= 1
    assert any(c["check_id"] == "C08_星标项覆盖" for c in report["issues"])
    print("✅ test_reviewer_execute_merges_deterministic_checks_when_llm_unavailable passed")


if __name__ == "__main__":
    print("Running Phase 5-7 requirement tests...\n")
    test_matcher_returns_tender_requirement_sources()
    test_generator_formats_matched_requirement_sources()
    test_tool_readiness_reports_missing_and_ready_states()
    test_chat_review_uses_readiness_before_running_tool()
    test_reviewer_deterministic_checks_include_locations()
    test_reviewer_execute_merges_deterministic_checks_when_llm_unavailable()
    print("\n🎉 All tests passed!")
