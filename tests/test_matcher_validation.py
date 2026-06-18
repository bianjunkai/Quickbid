"""
测试 MatcherAgent 的提纲验证功能（Phase 0）
手动测试脚本（无需 pytest）
"""
from agents.matcher_agent import validate_outline


def test_validation_empty_outline():
    """测试空提纲"""
    result = validate_outline([], {}, None)
    assert result["is_valid"] is False
    assert "提纲为空" in result["errors"]
    print("✅ test_validation_empty_outline passed")


def test_validation_scoring_coverage():
    """测试评分项覆盖度检查"""
    outline = [
        {
            "id": "ch1",
            "no": 1,
            "title": "公司资质",
            "category": "01_公司资质",
            "subsections": [],
        },
        {
            "id": "ch2",
            "no": 2,
            "title": "技术方案",
            "category": "03_技术方案",
            "subsections": [{"id": "ch2.1", "title": "系统架构设计"}],
        },
    ]
    scoring = {
        "dimensions": [
            {
                "name": "技术方案",
                "max_score": 30,
                "sub_items": [
                    {"name": "系统架构设计", "score": 10},
                    {"name": "数据库设计", "score": 5},  # 缺失
                ],
            }
        ]
    }
    result = validate_outline(outline, scoring, None)
    assert result["stats"]["scoring_coverage"] == 0.5
    assert any("数据库设计" in w for w in result["warnings"])
    print("✅ test_validation_scoring_coverage passed")


def test_validation_chapter_count():
    """测试章节数量合理性检查"""
    # 章节过少
    outline = [
        {"id": "ch1", "no": 1, "title": "公司资质", "category": "01_公司资质", "subsections": []}
    ]
    result = validate_outline(outline, {}, None)
    assert any("只有 1 个" in w for w in result["warnings"])

    # 小节过多
    outline = [
        {
            "id": "ch1",
            "no": 1,
            "title": "技术方案",
            "category": "03_技术方案",
            "subsections": [{"id": f"ch1.{i}", "title": f"小节{i}"} for i in range(15)],
        }
    ]
    result = validate_outline(outline, {}, None)
    assert any("15 个小节" in w for w in result["warnings"])
    print("✅ test_validation_chapter_count passed")


def test_validation_category_diversity():
    """测试分类多样性检查"""
    # 过度使用 06_其他
    outline = [
        {"id": f"ch{i}", "no": i, "title": f"章节{i}", "category": "06_其他", "subsections": []}
        for i in range(1, 6)
    ]
    result = validate_outline(outline, {}, None)
    assert any("归为『06_其他』" in w for w in result["warnings"])
    print("✅ test_validation_category_diversity passed")


def test_validation_duplicate_titles():
    """测试重复检查"""
    # 章节标题重复
    outline = [
        {"id": "ch1", "no": 1, "title": "技术方案", "category": "03_技术方案", "subsections": []},
        {"id": "ch2", "no": 2, "title": "技术方案", "category": "03_技术方案", "subsections": []},
    ]
    result = validate_outline(outline, {}, None)
    assert result["is_valid"] is False
    assert any("技术方案" in e for e in result["errors"])

    # 小节与章节重复
    outline = [
        {
            "id": "ch1",
            "no": 1,
            "title": "技术方案",
            "category": "03_技术方案",
            "subsections": [{"id": "ch1.1", "title": "技术方案"}],
        }
    ]
    result = validate_outline(outline, {}, None)
    assert any("与章节标题完全相同" in w for w in result["warnings"])
    print("✅ test_validation_duplicate_titles passed")


def test_validation_k12_compliance():
    """测试 K12 模板遵从检查"""
    outline = [
        {"id": "ch1", "no": 1, "title": "公司资质", "category": "01_公司资质", "subsections": []},
        {"id": "ch2", "no": 2, "title": "技术方案", "category": "03_技术方案", "subsections": []},
    ]
    k12 = """投标文件应包括以下内容：
    第一章：公司资质
    第二章：业绩案例
    第三章：技术方案
    第四章：实施方案
    """
    result = validate_outline(outline, {}, k12)
    # 应该警告缺少"业绩案例"和"实施方案"
    assert any("K12 要求的章节" in w for w in result["warnings"])
    print("✅ test_validation_k12_compliance passed")


def test_validation_stats():
    """测试统计信息"""
    outline = [
        {
            "id": "ch1",
            "no": 1,
            "title": "公司资质",
            "category": "01_公司资质",
            "subsections": [{"id": "ch1.1", "title": "营业执照"}],
        },
        {
            "id": "ch2",
            "no": 2,
            "title": "技术方案",
            "category": "03_技术方案",
            "subsections": [{"id": "ch2.1", "title": "架构设计"}],
        },
    ]
    result = validate_outline(outline, {}, None)
    stats = result["stats"]
    assert stats["chapter_count"] == 2
    assert stats["subsection_count"] == 2
    assert "01_公司资质" in stats["category_usage"]
    assert "03_技术方案" in stats["category_usage"]
    print("✅ test_validation_stats passed")


if __name__ == "__main__":
    print("Running MatcherAgent validation tests...\n")
    test_validation_empty_outline()
    test_validation_scoring_coverage()
    test_validation_chapter_count()
    test_validation_category_diversity()
    test_validation_duplicate_titles()
    test_validation_k12_compliance()
    test_validation_stats()
    print("\n🎉 All tests passed!")
