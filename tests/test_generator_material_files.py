"""
测试 GeneratorAgent 按 MatcherAgent 的 file_path 读取材料正文。

手动运行：
PYTHONPATH=. python3 tests/test_generator_material_files.py
"""
from pathlib import Path
from tempfile import TemporaryDirectory

from agents.generator_agent import GeneratorAgent


def test_load_md_material_from_file_path():
    with TemporaryDirectory() as tmp:
        material_path = Path(tmp) / "03_技术方案.md"
        material_path.write_text("医院信息化平台建设方案正文", encoding="utf-8")

        agent = GeneratorAgent()
        materials = agent._load_materials([
            {
                "file_path": str(material_path),
                "material_title": "技术方案",
                "category": "03_技术方案",
            }
        ])

        material = materials[str(material_path)]
        assert material["title"] == "技术方案"
        assert material["category"] == "03_技术方案"
        assert material["content"] == "医院信息化平台建设方案正文"

        formatted = agent._format_material(material)
        assert f"来源文件: {material_path}" in formatted
        assert "医院信息化平台建设方案正文" in formatted
        print("✅ test_load_md_material_from_file_path passed")


if __name__ == "__main__":
    print("Running GeneratorAgent material file tests...\n")
    test_load_md_material_from_file_path()
    print("\n🎉 All tests passed!")
