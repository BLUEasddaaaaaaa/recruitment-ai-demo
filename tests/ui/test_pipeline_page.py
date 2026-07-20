from src.domain.models import ApplicationStatus
from src.ui.pipeline_page import (
    application_table_rows,
    filter_application_rows,
    normalize_round_name,
    screening_status,
)


def test_screening_status_maps_hr_labels_to_application_states() -> None:
    assert screening_status("待定") is ApplicationStatus.SCREENING
    assert screening_status("通过") is ApplicationStatus.INTERVIEWING
    assert screening_status("拒绝") is ApplicationStatus.REJECTED


def test_normalize_round_name_defaults_blank_to_first_interview() -> None:
    assert normalize_round_name("") == "一面"
    assert normalize_round_name("  ") == "一面"
    assert normalize_round_name(" 技术二面 ") == "技术二面"


def test_application_table_rows_include_scan_and_selection_fields() -> None:
    class Candidate:
        id = 1
        name = "林晓"
        confirmed_by = "张HR"
        ai_metadata = {"intake": {"document": {"filename": "resume.pdf"}}}

    class Application:
        id = 7
        candidate_id = 1
        role = "数据分析师"
        department = "数据团队"
        status = ApplicationStatus.SCREENING

    rows = application_table_rows(
        [Application()],
        {1: Candidate()},
        {7: {"count": 2, "latest_outcome": "pass"}},
    )

    assert rows == [
        {
            "申请ID": 7,
            "候选人": "林晓",
            "HR": "张HR",
            "岗位": "数据分析师",
            "部门": "数据团队",
            "当前状态": "screening",
            "面试轮次": 2,
            "最近结论": "pass",
            "简历附件": "resume.pdf",
        }
    ]


def test_filter_application_rows_by_role_department_and_status() -> None:
    rows = [
        {"岗位": "数据分析师", "部门": "数据团队", "当前状态": "screening", "HR": "张HR"},
        {"岗位": "后端开发", "部门": "研发中心", "当前状态": "interviewing", "HR": "李HR"},
    ]

    assert filter_application_rows(rows, "数据分析师", "全部", "全部", "全部") == [rows[0]]
    assert filter_application_rows(rows, "全部", "研发中心", "interviewing", "全部") == [rows[1]]
    assert filter_application_rows(rows, "全部", "全部", "全部", "李HR") == [rows[1]]
