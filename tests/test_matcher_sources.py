"""
测试 MatcherAgent 的材料与招标要求来源匹配逻辑。

手动运行：
PYTHONPATH=. .venv/bin/python tests/test_matcher_sources.py
"""
from agents.base import AgentContext
from agents.matcher_agent import MatcherAgent


def test_matcher_matches_material_and_tender_sources():
    matcher = MatcherAgent()
    parsed_data = {
        "K12_章节模板要求": {
            "value": "投标文件应包括商务文件和技术方案",
            "source_page": 6,
        },
        "scoring": {
            "dimensions": [
                {
                    "name": "技术评分",
                    "source_page": 20,
                    "sub_items": [
                        {
                            "name": "系统架构",
                            "score": 5,
                            "criteria": "架构清晰、方案完整",
                        }
                    ],
                }
            ]
        },
    }
    outline = [
        {
            "id": "ch1",
            "no": 1,
            "title": "系统架构",
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

    ctx = AgentContext(project_id=1, parsed_data=parsed_data, outline=outline)
    result = matcher.match_materials(ctx)

    assert result["total"] == 2
    tech_sources = result["chapters"][0]["matched_sources"]
    commercial_sources = result["chapters"][1]["matched_sources"]
    assert any(s["source_type"] == "scoring_requirement" for s in tech_sources)
    assert any(s["source_type"] == "tender_template" for s in commercial_sources)

    scoring = next(s for s in tech_sources if s["source_type"] == "scoring_requirement")
    assert scoring["evidence"][0]["page"] == 20
    assert scoring["evidence"][0]["field_path"] == "scoring.dimensions[0].sub_items[0]"
    print("✅ test_matcher_matches_material_and_tender_sources passed")


if __name__ == "__main__":
    print("Running MatcherAgent source matching tests...\n")
    test_matcher_matches_material_and_tender_sources()
    print("\n🎉 All tests passed!")
