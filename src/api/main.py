from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from src.ai import create_ai_provider
from src.config import Settings
from src.db.repository import NotFoundError, Repository
from src.domain.models import InterviewInput, InterviewOutcome
from src.api import schemas
from src.api.serializers import serialize_candidate
from src.api.service import create_candidate_from_payload, parse_resume


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip().replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=__import__("datetime").timezone.utc)
        return parsed
    return None


def _build_dashboard(repository: Repository) -> dict[str, Any]:
    candidates = repository.list_candidates()
    applications = repository.list_applications()
    candidate_map = {c.id: c for c in candidates}
    interviews_by_app = {a.id: repository.list_interviews(a.id) for a in applications}

    todos: list[dict[str, Any]] = []
    for application in applications:
        candidate = candidate_map.get(application.candidate_id)
        if candidate is None:
            continue
        interviews = interviews_by_app.get(application.id, [])
        status_value = application.status.value
        if status_value in ("new", "screening"):
            todos.append(
                {
                    "id": f"todo-{application.id}",
                    "title": "待部门初筛",
                    "candidateName": candidate.name,
                    "jobTitle": application.role,
                    "department": application.department or "",
                    "suggestedAction": "发送简历给用人部门，并在企业微信群催办反馈",
                    "priority": "high",
                }
            )
        elif status_value == "interviewing" and not interviews:
            todos.append(
                {
                    "id": f"todo-{application.id}",
                    "title": "待安排面试",
                    "candidateName": candidate.name,
                    "jobTitle": application.role,
                    "department": application.department or "",
                    "suggestedAction": "确认面试官与面试时间，推进下一轮",
                    "priority": "medium",
                }
            )

    status_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    for application in applications:
        status_counts[application.status.value] = status_counts.get(application.status.value, 0) + 1
        role_counts[application.role] = role_counts.get(application.role, 0) + 1

    top_role = max(role_counts, key=role_counts.get) if role_counts else "暂无岗位"
    pending = status_counts.get("new", 0) + status_counts.get("screening", 0)
    interviewing = status_counts.get("interviewing", 0)
    offer = status_counts.get("offer", 0)

    insights = {
        "summary": f"当前共有 {len(candidates)} 名候选人、{len(applications)} 条申请，重点关注 {top_role}。",
        "bulletPoints": [
            f"筛选待处理 {pending} 条，面试中 {interviewing} 条，建议优先推进卡在筛选环节的候选人。",
            f"当前主招核心岗位：{top_role}。",
            "评价记录可继续沉淀为结构化数据，后续可训练岗位画像与面试通过率分析。",
        ],
        "suggestedFocusJob": top_role,
        "stuckCandidatesCount": pending,
    }
    report = (
        "企业微信招聘进展简报：\n"
        f"今日共有 {len(applications)} 条招聘申请，待筛选 {pending} 条，面试中 {interviewing} 条，已发Offer {offer} 条。\n"
        f"重点岗位：{top_role}。\n"
        "建议HR优先跟进待筛选候选人，并提醒用人部门及时反馈。"
    )
    return {
        "todos": todos[:8],
        "insights": insights,
        "report": report,
        "statusCounts": status_counts,
        "totalCandidates": len(candidates),
        "totalApplications": len(applications),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.removeprefix("sqlite:///")).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)
    repository = Repository(settings.database_url)
    provider = create_ai_provider(settings)
    app.state.settings = settings
    app.state.repository = repository
    app.state.provider = provider
    yield
    app.state.repository = None
    app.state.provider = None


app = FastAPI(title="招聘 AI Demo API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/resume/parse")
async def resume_parse(req: schemas.ResumeParseRequest, request: Request) -> dict[str, Any]:
    provider = request.app.state.provider
    try:
        return parse_resume(provider, req.text, req.fileName, req.fileContent)
    except Exception as exc:  # noqa: BLE001 - surface parser errors to the UI
        raise HTTPException(status_code=500, detail=f"简历解析失败: {exc}") from exc


@app.post("/api/candidates")
async def create_candidate(req: schemas.CandidateCreate, request: Request) -> dict[str, Any]:
    repository: Repository = request.app.state.repository
    try:
        return create_candidate_from_payload(repository, req)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"候选人入库失败: {exc}") from exc


@app.get("/api/candidates")
async def list_candidates(request: Request) -> list[dict[str, Any]]:
    repository: Repository = request.app.state.repository
    applications = repository.list_applications()
    result: list[dict[str, Any]] = []
    for application in applications:
        try:
            candidate = repository.get_candidate(application.candidate_id)
        except NotFoundError:
            continue
        interviews = repository.list_interviews(application.id)
        result.append(serialize_candidate(candidate, application, interviews))
    result.sort(key=lambda item: int(item["id"]), reverse=True)
    return result


@app.get("/api/candidates/{candidate_id}")
async def candidate_detail(candidate_id: int, request: Request) -> dict[str, Any]:
    repository: Repository = request.app.state.repository
    try:
        application = repository.get_application(candidate_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="候选人申请不存在") from exc
    candidate = repository.get_candidate(application.candidate_id)
    interviews = repository.list_interviews(application.id)
    return serialize_candidate(candidate, application, interviews)


@app.put("/api/applications/{application_id}/status")
async def update_status(
    application_id: int, body: schemas.StatusUpdate, request: Request
) -> dict[str, Any]:
    repository: Repository = request.app.state.repository
    try:
        application = repository.update_application_status(application_id, body.status)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="申请不存在") from exc
    repository.append_audit_event(
        "application_status_updated",
        entity_type="application",
        entity_id=str(application.id),
        actor="HR",
        payload={"status": body.status},
    )
    candidate = repository.get_candidate(application.candidate_id)
    interviews = repository.list_interviews(application.id)
    return serialize_candidate(candidate, application, interviews)


@app.post("/api/applications/{application_id}/interviews")
async def add_interview(
    application_id: int, body: schemas.InterviewCreate, request: Request
) -> dict[str, Any]:
    repository: Repository = request.app.state.repository
    interview = InterviewInput(
        round_name=f"第{body.round}轮",
        interviewer=body.interviewer,
        scheduled_at=_parse_date(body.date),
        outcome=InterviewOutcome(body.result),
        notes=body.feedback,
        metadata={"date": body.date, "round_index": body.round},
    )
    try:
        repository.append_interview(application_id, interview)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="申请不存在") from exc
    application = repository.get_application(application_id)
    candidate = repository.get_candidate(application.candidate_id)
    interviews = repository.list_interviews(application.id)
    return serialize_candidate(candidate, application, interviews)


@app.get("/api/ai/dashboard")
async def ai_dashboard(request: Request) -> dict[str, Any]:
    repository: Repository = request.app.state.repository
    return _build_dashboard(repository)


@app.get("/api/ai/insights")
async def ai_insights(request: Request) -> dict[str, Any]:
    # Backwards-compatible alias used by the previous front-end build.
    repository: Repository = request.app.state.repository
    return _build_dashboard(repository)


@app.delete("/api/candidates/{candidate_id}")
async def delete_candidate(candidate_id: int, request: Request) -> dict[str, Any]:
    repository: Repository = request.app.state.repository
    try:
        application = repository.get_application(candidate_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="候选人申请不存在") from exc
    repository.delete_candidate(application.candidate_id)
    return {"success": True}
