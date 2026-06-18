"""
测试 review 前置条件失败时不会写成 reviewed。

手动运行：
PYTHONPATH=. python3 tests/test_review_status.py
"""
import os
from tempfile import TemporaryDirectory

_tmp = TemporaryDirectory()
os.environ["TENDER_DB_PATH"] = os.path.join(_tmp.name, "review_status.db")

import main  # noqa: E402
from models import Project, Tender, get_session, init_db  # noqa: E402
from orchestrator import Orchestrator  # noqa: E402


def _create_project_and_tender() -> tuple[int, int]:
    init_db()
    session = get_session()
    project = Project(
        name="测试项目",
        tender_file_path=os.path.join(_tmp.name, "tender.pdf"),
        status="generated",
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    tender = Tender(project_id=project.id, type="main", status="generated")
    session.add(tender)
    session.commit()
    session.refresh(tender)
    return project.id, tender.id


def test_rest_review_error_sets_review_failed():
    project_id, tender_id = _create_project_and_tender()

    result = main.review_tender(tender_id)

    session = get_session()
    project = session.get(Project, project_id)
    tender = session.get(Tender, tender_id)
    assert result["error"]
    assert result["message"].startswith("终审失败")
    assert project.status == "review_failed"
    assert tender.status == "review_failed"
    print("✅ test_rest_review_error_sets_review_failed passed")


def test_orchestrator_review_error_sets_review_failed():
    project_id, tender_id = _create_project_and_tender()
    orch = Orchestrator({})
    orch.ctx.project_id = project_id
    orch.ctx.tender_id = tender_id

    result = orch._run_review()

    session = get_session()
    project = session.get(Project, project_id)
    tender = session.get(Tender, tender_id)
    assert result["review"]["error"]
    assert project.status == "review_failed"
    assert tender.status == "review_failed"
    print("✅ test_orchestrator_review_error_sets_review_failed passed")


if __name__ == "__main__":
    print("Running review status tests...\n")
    test_rest_review_error_sets_review_failed()
    test_orchestrator_review_error_sets_review_failed()
    print("\n🎉 All tests passed!")
