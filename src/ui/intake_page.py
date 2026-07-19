from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

from src.domain.models import CandidateDraft
from src.services.intake import ConfirmationChoice, IntakeError, IntakeService, PreparedIntake


def _plain(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if hasattr(value, "items"):
        return {key: _plain(item) for key, item in value.items()}
    return value


def _json_list(value: str, field_name: str) -> list[Any]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError as error:
        raise ValueError(f"{field_name} 必须是有效 JSON") from error
    if not isinstance(parsed, list):
        raise ValueError(f"{field_name} 必须是 JSON 列表")
    return parsed


def _render_evidence(prepared: PreparedIntake) -> None:
    rows = [
        {
            "字段": field,
            "来源": evidence.source,
            "证据摘要": evidence.quote,
            "置信度": evidence.confidence,
        }
        for field, evidence in prepared.draft.field_sources.items()
    ]
    if rows:
        st.caption("AI 字段来源（仅展示证据摘要）")
        st.dataframe(rows, use_container_width=True, hide_index=True)
    if prepared.conflicts:
        st.warning("发现简历与 BOSS 备注冲突，请 HR 核对后编辑。")
        for item in prepared.conflicts:
            st.write(f"- {item.field_name}: 简历“{item.resume_value}” / 备注“{item.note_value}”")


def render_intake_page(service: IntakeService, sample_path: Path) -> None:
    st.header("简历录入")
    st.caption(f"演示样本：{sample_path}")
    uploaded = st.file_uploader("匿名化简历", type=["txt", "pdf", "docx", "png", "jpg", "jpeg"])
    use_sample = st.checkbox("使用内置匿名样本（无需上传）")
    role = st.text_input("应聘岗位", placeholder="数据分析师")
    department = st.text_input("用人部门", placeholder="数据团队")
    notes = st.text_area("BOSS 备注", placeholder="例如：期望薪资 20k，两周到岗")

    if st.button("AI预填", type="primary"):
        if not role.strip():
            st.error("请先填写应聘岗位。")
        elif uploaded is None and not use_sample:
            st.error("请上传匿名简历，或勾选内置匿名样本。")
        else:
            try:
                filename = sample_path.name if use_sample else uploaded.name
                content = sample_path.read_bytes() if use_sample else uploaded.getvalue()
                st.session_state["prepared_intake"] = service.prepare_draft(
                    filename, content, notes, role, department=department
                )
                st.session_state["intake_idempotency_key"] = uuid4().hex
            except (IntakeError, OSError, ValueError) as error:
                st.error(f"无法生成预填草稿：{error}")

    prepared: PreparedIntake | None = st.session_state.get("prepared_intake")
    if prepared is None:
        return

    st.subheader("HR 核对与确认")
    st.caption(
        f"附件：{prepared.document.filename} · {prepared.document.mime_type} · "
        f"引用 {prepared.document.attachment_reference[:24]}…"
    )
    _render_evidence(prepared)
    draft = prepared.draft
    with st.form("confirm_intake"):
        name = st.text_input("姓名 *", value=draft.name or "")
        phone = st.text_input("电话", value=draft.phone or "")
        email = st.text_input("邮箱", value=draft.email or "")
        city = st.text_input("当前城市", value=draft.current_city or "")
        salary = st.text_input("期望薪资", value=draft.expected_salary or "")
        availability = st.text_input("到岗时间", value=draft.availability or "")
        skills = st.text_input("技能（逗号分隔）", value=", ".join(draft.skills))
        education = st.text_area(
            "教育经历（JSON 列表）", value=json.dumps(_plain(draft.education), ensure_ascii=False)
        )
        experience = st.text_area(
            "工作经历（JSON 列表）",
            value=json.dumps(_plain(draft.work_experience), ensure_ascii=False),
        )
        actor = st.text_input("HR 姓名 *")

        selected_candidate_id = None
        if prepared.duplicate_hints:
            st.warning("发现疑似重复候选人，必须明确选择处理方式。")
            labels = {
                f"#{hint.candidate_id} {hint.display_name}（匹配：{', '.join(hint.matched_fields)}）": hint.candidate_id
                for hint in prepared.duplicate_hints
            }
            resolution = st.radio("重复处理", ["复用已有候选人", "仍创建新候选人"])
            if resolution == "复用已有候选人":
                selected_candidate_id = labels[st.selectbox("选择已有候选人", list(labels))]
                choice = ConfirmationChoice.REUSE_DUPLICATE
            else:
                choice = ConfirmationChoice.CREATE_NEW
        else:
            st.success("未发现手机号或邮箱重复提示。")
            st.radio("重复处理", ["确认无重复"], disabled=True)
            choice = ConfirmationChoice.NO_DUPLICATE
        submitted = st.form_submit_button("HR确认入库", type="primary")

    if submitted:
        try:
            edited = CandidateDraft.model_validate(
                {
                    **draft.model_dump(mode="python"),
                    "name": name,
                    "phone": phone or None,
                    "email": email or None,
                    "current_city": city or None,
                    "expected_salary": salary or None,
                    "availability": availability or None,
                    "skills": [item.strip() for item in skills.split(",") if item.strip()],
                    "education": _json_list(education, "教育经历"),
                    "work_experience": _json_list(experience, "工作经历"),
                }
            )
            candidate, application = service.confirm(
                prepared.token,
                confirmed_by=actor,
                choice=choice,
                confirmed=edited,
                selected_candidate_id=selected_candidate_id,
                idempotency_key=st.session_state["intake_idempotency_key"],
            )
            st.success(f"入库成功：候选人 #{candidate.id}，申请 #{application.id}。")
            st.session_state.pop("prepared_intake", None)
            st.session_state.pop("intake_idempotency_key", None)
        except (IntakeError, ValueError) as error:
            st.error(f"确认失败：{error}")
