from __future__ import annotations

import hashlib
import re
from datetime import datetime, UTC
from typing import Any

from src.ai.protocol import AIProvider
from src.db.models import utc_now
from src.db.repository import Repository
from src.documents.extract_text import ExtractedDocument, UnsupportedDocument, extract_document
from src.domain.models import ApplicationStatus, CandidateConfirmed, FieldEvidence
from src.api.schemas import CandidateCreate


# --------------------------------------------------------------------------- #
# Resume parsing
# --------------------------------------------------------------------------- #
def parse_resume(
    provider: AIProvider,
    text: str,
    file_name: str | None,
    file_content: str | None = None,
) -> dict[str, Any]:
    filename = file_name or "resume.txt"

    # If a binary/base64 file payload was supplied, decode it and try to
    # extract the real text with python-docx / pypdf before sending to AI.
    extracted_text = text
    if file_content:
        try:
            import base64

            content = base64.b64decode(file_content)
            document = extract_document(filename, content)
            extracted_text = document.text or text
        except UnsupportedDocument:
            # Fall back to the text payload the front-end also sent.
            pass

    # For plain text or a malformed file we still want to run extraction
    # (it validates length / encoding safely).
    if not extracted_text:
        extracted_text = text

    try:
        document = extract_document(filename, extracted_text.encode("utf-8"))
    except UnsupportedDocument:
        document = ExtractedDocument(filename=filename, mime_type="text/plain", text=extracted_text)

    result = provider.extract_candidate(document.text, "", list(document.image_bytes))
    draft = result.draft
    parsed = _draft_to_parsed(draft, document.text)
    parsed["extractedText"] = document.text
    return parsed


def _extract_job_title(text: str) -> str | None:
    match = re.search(
        r"(?:求职意向|求职岗位|应聘岗位|应聘职位|求职：|岗位)[:：]?\s*([^\n；;，,（(]+)",
        text,
    )
    if not match:
        return None
    value = match.group(1).strip()
    # Keep only the part before a department hint like "研发部 / 前端技术部"
    value = re.split(r"[/／]", value)[0].strip(" /／")
    return value or None


def _infer_department(text: str) -> tuple[str, str]:
    lower = text.lower()
    if any(k in lower for k in ("算法", "ai", "nlp", "pytorch", "tensorflow", "深度学习", "大模型", "cv", "机器学习", "llm", "rag")):
        return "AI研究部", "low"
    if any(k in lower for k in ("数据", "sql", "分析", "tableau", "数仓", "bi", "analytics", "etl")):
        return "数据部", "low"
    if any(k in lower for k in ("产品", "需求", "策划", "prd", "product")):
        return "产品部", "low"
    if any(k in lower for k in ("运营", "市场", "增长", "活动", "新媒体", "私域")):
        return "运营部", "low"
    if any(k in lower for k in ("前端", "后端", "开发", "java", "工程师", "c++", "测试", "python", "node")):
        return "研发部", "low"
    return "待定", "low"


def _infer_job_title(text: str) -> str:
    if any(k in text.lower() for k in ("算法", "nlp", "深度学习", "大模型")):
        return "算法工程师"
    if any(k in text.lower() for k in ("数据", "分析", "bi", "sql")):
        return "数据分析师"
    if any(k in text.lower() for k in ("产品", "策划")):
        return "产品经理"
    if any(k in text.lower() for k in ("运营", "市场", "增长")):
        return "运营专员"
    if any(k in text.lower() for k in ("前端", "后端", "开发", "java", "工程师")):
        return "开发工程师"
    return "待定"


def _stringify_education(entries: list[dict[str, Any]]) -> str:
    parts = []
    for entry in entries or []:
        seg = " ".join(
            str(entry[k])
            for k in ("school", "degree", "major", "start_date", "end_date")
            if entry.get(k)
        )
        if seg:
            parts.append(seg)
    return "；".join(parts)


def _stringify_work(entries: list[dict[str, Any]]) -> str:
    parts = []
    for entry in entries or []:
        head = " ".join(
            str(entry[k]) for k in ("company", "title", "start_date", "end_date") if entry.get(k)
        )
        descriptions = entry.get("description") or []
        if isinstance(descriptions, list):
            head += "：" + "；".join(str(d) for d in descriptions if d)
        if head.strip():
            parts.append(head.strip("："))
    return "\n".join(parts)


def _draft_to_parsed(draft: Any, text: str) -> dict[str, Any]:
    name = draft.name or ""
    phone = draft.phone or ""
    email = draft.email or ""

    extracted_title = _extract_job_title(text)
    job_title = extracted_title or _infer_job_title(text)
    department, _dept_conf = _infer_department(text)

    education = _stringify_education(getattr(draft, "education", []) or [])
    experience = _stringify_work(getattr(draft, "work_experience", []) or [])
    skills = list(getattr(draft, "skills", []) or [])

    summary = (draft.ai_metadata or {}).get("summary")
    if not summary:
        summary = ("候选人技能：" + "、".join(skills)) if skills else "AI 已完成简历结构化解析，请 HR 核实关键字段。"

    sources = draft.field_sources or {}

    def conf(field: str) -> str:
        evidence = sources.get(field)
        if evidence is not None:
            return "high" if (getattr(evidence, "confidence", 0) or 0) >= 0.8 else "low"
        return "high" if getattr(draft, field, None) else "low"

    confidence = {
        "name": conf("name"),
        "phone": conf("phone"),
        "email": conf("email"),
        "jobTitle": "high" if extracted_title else "low",
        "department": "low",
        "education": "high" if getattr(draft, "education", None) else "low",
        "experience": "high" if getattr(draft, "work_experience", None) else "low",
    }

    return {
        "name": name,
        "phone": phone,
        "email": email,
        "jobTitle": job_title,
        "department": department,
        "education": education,
        "experience": experience,
        "skills": skills,
        "summary": summary,
        "confidence": confidence,
    }


# --------------------------------------------------------------------------- #
# Candidate creation
# --------------------------------------------------------------------------- #
def create_candidate_from_payload(repository: Repository, payload: CandidateCreate) -> dict[str, Any]:
    now = utc_now()
    meta: dict[str, Any] = {
        "resume_text": payload.resumeText or "",
        "resume_file_name": payload.resumeFileName or "",
        "summary": payload.summary or "",
        "confidence": payload.confidence or {},
        "intake": {"source": "react_frontend", "confirmed_at": now.isoformat()},
    }

    def fe(value: Any, source: str = "hr_confirmed") -> FieldEvidence:
        return FieldEvidence(source=source, quote=str(value) if value else "", confidence=1.0)

    field_sources: dict[str, FieldEvidence] = {"name": fe(payload.name)}
    if payload.phone:
        field_sources["phone"] = fe(payload.phone)
    if payload.email:
        field_sources["email"] = fe(payload.email)

    values: dict[str, Any] = {
        "name": payload.name,
        "phone": payload.phone,
        "email": payload.email,
        "confirmed_by": payload.hrName or "HR",
        "confirmed_at": now,
        "education": [{"description": payload.education}] if payload.education else [],
        "work_experience": [{"description": payload.experience}] if payload.experience else [],
        "skills": list(payload.skills or []),
        "expected_salary": payload.expectedSalary,
        "availability": payload.availability,
        "source_channel": payload.sourceChannel,
        "hr_notes": "",
        "field_sources": field_sources,
        "ai_metadata": meta,
    }
    confirmed = CandidateConfirmed.model_validate(values)

    candidate = repository.create_candidate(confirmed)
    status = ApplicationStatus(payload.status) if payload.status else ApplicationStatus.NEW
    application = repository.create_application(
        candidate.id,
        role=payload.jobTitle or "待定",
        department=payload.department,
        status=status,
    )

    actor = payload.hrName or "HR"
    repository.append_audit_event(
        "candidate_intake_confirmed",
        entity_type="application",
        entity_id=str(application.id),
        actor=actor,
        payload={"candidate_id": candidate.id, "source": "react_frontend"},
    )

    sha = hashlib.sha256((payload.resumeText or "").encode("utf-8")).hexdigest()
    repository.upsert_sync_job(
        "candidate_docs",
        f"intake:react:{application.id}:candidate-docs",
        status="pending",
        payload={
            "candidate_id": candidate.id,
            "application_id": application.id,
            "document": {
                "display_name": payload.resumeFileName or "resume.txt",
                "sha256": sha,
            },
        },
    )
    repository.upsert_sync_job(
        "department_notification",
        f"intake:react:{application.id}:department-notification",
        status="pending",
        payload={"candidate_id": candidate.id, "application_id": application.id},
    )

    interviews = repository.list_interviews(application.id)
    from src.api.serializers import serialize_candidate

    return serialize_candidate(candidate, application, interviews)
