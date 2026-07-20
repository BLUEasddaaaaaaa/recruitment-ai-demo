from __future__ import annotations

import streamlit as st

from src.db.repository import Repository


def build_ai_dashboard(
    candidates: list[object],
    applications: list[object],
    candidate_map: dict[int, object],
    interviews_by_application: dict[int, list[object]],
) -> dict[str, object]:
    todos = []
    for app in applications:
        candidate = candidate_map[app.candidate_id]
        interviews = interviews_by_application.get(app.id, [])
        if app.status.value in {"new", "screening"}:
            todos.append(
                {
                    "事项": "待部门筛选",
                    "候选人": candidate.name,
                    "岗位": app.role,
                    "建议动作": "发送简历给用人部门，并在企业微信群催办反馈",
                }
            )
        elif app.status.value == "interviewing" and not interviews:
            todos.append(
                {
                    "事项": "待安排面试",
                    "候选人": candidate.name,
                    "岗位": app.role,
                    "建议动作": "确认面试官和面试时间",
                }
            )

    status_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    for app in applications:
        status_counts[app.status.value] = status_counts.get(app.status.value, 0) + 1
        role_counts[app.role] = role_counts.get(app.role, 0) + 1
    top_role = max(role_counts, key=role_counts.get) if role_counts else "暂无岗位"
    pending = status_counts.get("new", 0) + status_counts.get("screening", 0)
    interviewing = status_counts.get("interviewing", 0)

    insights = [
        f"AI运营洞察：当前共有 {len(candidates)} 名候选人、{len(applications)} 条申请，重点关注 {top_role}。",
        f"筛选待处理 {pending} 条，面试中 {interviewing} 条，建议优先推进卡在筛选环节的候选人。",
        "评价记录可继续沉淀为结构化数据，后续可训练岗位画像和面试通过率分析。",
    ]
    report = (
        "企业微信招聘进展简报：\n"
        f"今日共有 {len(applications)} 条招聘申请，待筛选 {pending} 条，面试中 {interviewing} 条。\n"
        f"重点岗位：{top_role}。\n"
        "建议HR优先跟进待筛选候选人，并提醒用人部门及时反馈。"
    )
    return {"todos": todos[:8], "insights": insights, "report": report}


def render_dashboard_page(repository: Repository) -> None:
    st.header("AI 招聘运营助手")
    candidates = repository.list_candidates()
    applications = repository.list_applications()
    candidate_map = {candidate.id: candidate for candidate in candidates}
    interviews_by_application = {app.id: repository.list_interviews(app.id) for app in applications}
    aggregates = repository.dashboard_aggregates()
    cols = st.columns(3)
    cols[0].metric("候选人总数", len(candidates))
    cols[1].metric("申请总数", len(applications))
    cols[2].metric("同步异常", aggregates.sync_failure_count)
    if not applications:
        st.info("确认候选人后，这里会生成AI待办、洞察和企业微信汇报。")
        return

    dashboard = build_ai_dashboard(
        candidates, applications, candidate_map, interviews_by_application
    )
    st.subheader("今日待办")
    st.dataframe(dashboard["todos"], use_container_width=True, hide_index=True)

    st.subheader("AI运营洞察")
    for insight in dashboard["insights"]:
        st.info(insight)

    st.subheader("一键生成汇报")
    st.text_area("可复制到企业微信群", value=dashboard["report"], height=180)
