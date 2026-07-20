from src.domain.models import ApplicationStatus
from src.ui.dashboard_page import build_ai_dashboard


def test_build_ai_dashboard_returns_todos_insights_and_report() -> None:
    class Candidate:
        name = "林晓"

    class Application:
        id = 1
        candidate_id = 1
        role = "数据分析师"
        department = "数据团队"
        status = ApplicationStatus.SCREENING

    result = build_ai_dashboard([Candidate()], [Application()], {1: Candidate()}, {1: []})

    assert result["todos"][0]["事项"] == "待部门筛选"
    assert "AI运营洞察" in result["insights"][0]
    assert "企业微信" in result["report"]
