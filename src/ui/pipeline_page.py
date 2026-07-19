from __future__ import annotations

import streamlit as st

from src.db.repository import Repository, RepositoryError
from src.domain.models import ApplicationStatus, InterviewInput, InterviewOutcome


def screening_status(label: str) -> ApplicationStatus:
    return {
        "待定": ApplicationStatus.SCREENING,
        "通过": ApplicationStatus.INTERVIEWING,
        "拒绝": ApplicationStatus.REJECTED,
    }[label]


def normalize_round_name(value: str) -> str:
    return value.strip() or "一面"


def application_table_rows(
    applications: list[object],
    candidates: dict[int, object],
    interview_summaries: dict[int, dict[str, object]],
) -> list[dict[str, object]]:
    rows = []
    for app in applications:
        candidate = candidates[app.candidate_id]
        document = candidate.ai_metadata.get("intake", {}).get("document", {})
        summary = interview_summaries.get(app.id, {})
        rows.append(
            {
                "申请ID": app.id,
                "候选人": candidate.name,
                "HR": candidate.confirmed_by or "未记录",
                "岗位": app.role,
                "部门": app.department or "未设置",
                "当前状态": app.status.value,
                "面试轮次": summary.get("count", 0),
                "最近结论": summary.get("latest_outcome", "暂无"),
                "简历附件": document.get("filename", "无"),
            }
        )
    return rows


def filter_application_rows(
    rows: list[dict[str, object]], role: str, department: str, status: str, hr: str
) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if (role == "全部" or row["岗位"] == role)
        and (department == "全部" or row["部门"] == department)
        and (status == "全部" or row["当前状态"] == status)
        and (hr == "全部" or row["HR"] == hr)
    ]


def render_pipeline_page(repository: Repository) -> None:
    st.header("候选人流程")
    candidates = {candidate.id: candidate for candidate in repository.list_candidates()}
    applications = repository.list_applications()
    if not applications:
        st.info("暂无申请，请先在“简历录入”完成一条匿名样本。")
        return
    interview_summaries = {}
    for app in applications:
        interviews = repository.list_interviews(app.id)
        interview_summaries[app.id] = {
            "count": len(interviews),
            "latest_outcome": interviews[-1].outcome.value if interviews else "暂无",
        }

    rows = application_table_rows(applications, candidates, interview_summaries)
    f1, f2, f3, f4 = st.columns(4)
    role_filter = f1.selectbox("岗位筛选", ["全部"] + sorted({str(row["岗位"]) for row in rows}))
    department_filter = f2.selectbox(
        "部门筛选", ["全部"] + sorted({str(row["部门"]) for row in rows})
    )
    status_filter = f3.selectbox(
        "状态筛选", ["全部"] + sorted({str(row["当前状态"]) for row in rows})
    )
    hr_filter = f4.selectbox("HR筛选", ["全部"] + sorted({str(row["HR"]) for row in rows}))
    rows = filter_application_rows(rows, role_filter, department_filter, status_filter, hr_filter)
    if not rows:
        st.info("当前筛选条件下暂无候选人申请。")
        return

    event = st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="applications_table",
    )
    selected_rows = event.selection.rows if event and event.selection else []
    if not selected_rows:
        st.info("点击上方表格中的一行后，可更新筛选状态或追加面试记录。")
        return

    application_id = rows[selected_rows[0]]["申请ID"]
    application = repository.get_application(application_id)
    candidate = candidates[application.candidate_id]
    cols = st.columns(4)
    cols[0].metric("候选人", candidate.name)
    cols[1].metric("岗位", application.role)
    cols[2].metric("部门", application.department or "未设置")
    cols[3].metric("当前状态", application.status.value)

    document = candidate.ai_metadata.get("intake", {}).get("document", {})
    if document:
        st.caption(
            f"简历附件元数据：{document.get('filename', 'resume')} · "
            f"{document.get('mime_type', '未知类型')} · "
            f"引用 {document.get('attachment_reference', '无')}"
        )

    with st.form("screening_status"):
        label = st.radio("部门筛选", ["待定", "通过", "拒绝"], horizontal=True)
        actor = st.text_input("操作人", key="screening_actor")
        update = st.form_submit_button("更新筛选状态")
    if update:
        if not actor.strip():
            st.error("请填写操作人。")
        else:
            repository.update_application_status(application_id, screening_status(label))
            repository.append_audit_event(
                "department_screening_updated",
                entity_type="application",
                entity_id=str(application_id),
                actor=actor,
                payload={"screening": label},
            )
            st.success("筛选状态已更新，历史记录已保留。")

    st.subheader("面试轮次")
    interviews = repository.list_interviews(application_id)
    if interviews:
        st.dataframe(
            [
                {
                    "轮次": item.round_name,
                    "面试官": item.interviewer,
                    "评价": item.notes,
                    "结论": item.outcome.value,
                    "记录时间": item.created_at,
                }
                for item in interviews
            ],
            use_container_width=True,
            hide_index=True,
        )
    with st.form("append_interview", clear_on_submit=True):
        round_name = st.text_input("轮次", value="一面")
        interviewer = st.text_input("面试官")
        evaluation = st.text_area("评价")
        outcome_label = st.selectbox("结论", ["待定", "通过", "不通过", "保留"])
        append = st.form_submit_button("追加面试记录")
    if append:
        outcomes = {
            "待定": InterviewOutcome.PENDING,
            "通过": InterviewOutcome.PASS,
            "不通过": InterviewOutcome.FAIL,
            "保留": InterviewOutcome.HOLD,
        }
        try:
            repository.append_interview(
                application_id,
                InterviewInput(
                    round_name=normalize_round_name(round_name),
                    interviewer=interviewer or None,
                    notes=evaluation or None,
                    outcome=outcomes[outcome_label],
                ),
            )
            st.success("面试记录已追加。")
        except (RepositoryError, ValueError) as error:
            st.error(f"无法追加记录：{error}")
