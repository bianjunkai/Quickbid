"""
测试项目删除会同步清理 projects/ 下的运行时目录。

手动运行：
PYTHONPATH=. python3 tests/test_delete_project.py
"""
from pathlib import Path
from tempfile import TemporaryDirectory

import main
import models
from models import Project, Tender, get_session, init_db


def test_delete_project_removes_runtime_directory():
    with TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        old_db_path = models.DB_PATH
        old_projects_dir = main.PROJECTS_DIR
        models.DB_PATH = str(tmp_dir / "tender.db")
        main.PROJECTS_DIR = tmp_dir / "projects"
        main.PROJECTS_DIR.mkdir(parents=True)

        try:
            init_db()
            project_dir = main.PROJECTS_DIR / "20260625_delete_test"
            tender_path = project_dir / "tender.pdf"
            draft_path = project_dir / "main" / "draft.md"
            draft_path.parent.mkdir(parents=True)
            tender_path.write_text("placeholder tender", encoding="utf-8")
            draft_path.write_text("# draft", encoding="utf-8")

            session = get_session()
            project = Project(
                name="删除测试项目",
                tender_file_path=str(tender_path),
                status="parsed",
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            project_id = project.id
            session.add(Tender(project_id=project_id, type="main", draft_path=str(draft_path)))
            session.commit()
            session.close()

            result = main.delete_project(project_id)

            assert result["message"] == "项目已删除"
            assert result["deleted_project_dir"] == str(project_dir.resolve())
            assert not project_dir.exists()

            verify_session = get_session()
            try:
                assert verify_session.get(Project, project_id) is None
                assert (
                    verify_session.query(Tender)
                    .filter(Tender.project_id == project_id)
                    .count()
                    == 0
                )
            finally:
                verify_session.close()
        finally:
            models.DB_PATH = old_db_path
            main.PROJECTS_DIR = old_projects_dir

    print("✅ test_delete_project_removes_runtime_directory passed")


if __name__ == "__main__":
    print("Running project deletion tests...\n")
    test_delete_project_removes_runtime_directory()
    print("\n🎉 All tests passed!")
