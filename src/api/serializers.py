from __future__ import annotations

from datetime import datetime
from typing import Any

from src.db.models import ApplicationRow, CandidateRow, InterviewRoundRow
from src.domain.models import ApplicationStatus, InterviewOutcome


def _dt_to_str(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is not None:
        value = value.astimezone()
    return value.strftime("%Y-%m-%d %H:%M")


def _meta(row: CandidateRow) -> dict[str, Any]:
    return row.ai_metadata or {}


def _derive_latest_conclusion(status: str, interviews: list[dict[str, Any]]) -> str:
    if interviews:
        last = interviews[-1]
        round_no = last.get("round") or len(interviews)
        feedback = (last.get("feedback") or "").strip()
        if last.get("result") == "pass":
            snippet = feedback[:30] + ("..." if len(feedback) > 30 else "")
            return f"{round_no}轮面试通过，反馈: {snippet}"
        if last.get("result") == "fail":
            return f"{round_no}轮淘汰: {feedback}"
        return f"已安排{round_no}轮面试: {last.get('interviewer') or '面试官'}"
    return {
        "new": "新申请待处理",
        "screening": "简历已入库，等待用人部门筛选",
        "interviewing": "面试流程进行中",
        "offer": "已发放 Offer",
        "hired": "候选人已入职",
        "rejected": "流程已结束（未通过）",
        "withdrawn": "候选人已撤回",
    }.get(status, "流程进行中")


def serialize_interview(iv: InterviewRoundRow, fallback_round: int) -> dict[str, Any]:
    outcome = iv.outcome.value if isinstance(iv.outcome, InterviewOutcome) else str(iv.outcome)
    result = outcome if outcome in ("pass", "fail", "pending") else "pending"
    meta = iv.metadata_json or {}
    round_index = meta.get("round_index")
    if round_index is None:
        round_index = fallback_round
    date = meta.get("date") or _dt_to_str(iv.scheduled_at) or _dt_to_str(iv.created_at)
    return {
        "id": str(iv.id),
        "round": int(round_index),
        "interviewer": iv.interviewer or "",
        "date": date,
        "result": result,
        "feedback": iv.notes or "",
    }


def serialize_candidate(
    candidate: CandidateRow,
    application: ApplicationRow,
    interviews: list[InterviewRoundRow],
) -> dict[str, Any]:
    meta = _meta(candidate)
    interview_list = [
        serialize_interview(iv, idx + 1) for idx, iv in enumerate(interviews)
    ]
    status = application.status.value if isinstance(application.status, ApplicationStatus) else str(application.status)
    latest = meta.get("latest_conclusion") or _derive_latest_conclusion(status, interview_list)
    return {
        "id": str(application.id),
        "name": candidate.name,
        "phone": candidate.phone or "",
        "email": candidate.email or "",
        "hrName": candidate.confirmed_by or "",
        "jobTitle": application.role,
        "department": application.department or "",
        "status": status,
        "currentRound": len(interview_list),
        "latestConclusion": latest,
        "resumeFileName": meta.get("resume_file_name") or "",
        "resumeText": meta.get("resume_text") or "",
        "interviews": interview_list,
        "createdAt": _dt_to_str(candidate.created_at),
    }
