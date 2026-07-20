from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlalchemy.types import DateTime, TypeDecorator
from sqlmodel import Field, SQLModel

from src.domain.models import ApplicationStatus, InterviewOutcome, SyncStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Portable aware-UTC timestamps, including when SQLite drops offsets."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("datetime must be timezone-aware")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def timestamp_field() -> Any:
    return Field(default_factory=utc_now, sa_type=UTCDateTime())


class CandidateRow(SQLModel, table=True):
    __tablename__ = "candidates"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    phone: str | None = Field(default=None, index=True)
    phone_normalized: str | None = Field(default=None, index=True)
    email: str | None = Field(default=None, index=True)
    email_normalized: str | None = Field(default=None, index=True)
    current_city: str | None = None
    education: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    work_experience: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    internship_experience: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    project_experience: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    skills: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    expected_salary: str | None = None
    availability: str | None = None
    source_channel: str | None = None
    hr_notes: str | None = None
    field_sources: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    ai_model: str | None = None
    ai_request_id: str | None = None
    ai_generated_at: datetime | None = Field(default=None, sa_type=UTCDateTime())
    ai_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    confirmed_by: str | None = None
    confirmed_at: datetime | None = Field(default=None, sa_type=UTCDateTime())
    confirmation_notes: str | None = None
    created_at: datetime = timestamp_field()
    updated_at: datetime = timestamp_field()


class ApplicationRow(SQLModel, table=True):
    __tablename__ = "applications"

    id: int | None = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidates.id", index=True)
    role: str
    department: str | None = None
    status: ApplicationStatus = Field(default=ApplicationStatus.NEW, index=True)
    template_id: int | None = Field(default=None, foreign_key="role_templates.id")
    created_at: datetime = timestamp_field()
    updated_at: datetime = timestamp_field()


class InterviewRoundRow(SQLModel, table=True):
    __tablename__ = "interview_rounds"

    id: int | None = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="applications.id", index=True)
    round_name: str
    interviewer: str | None = None
    scheduled_at: datetime | None = Field(default=None, sa_type=UTCDateTime())
    outcome: InterviewOutcome = InterviewOutcome.PENDING
    notes: str | None = None
    feedback: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = timestamp_field()


class RoleTemplateRow(SQLModel, table=True):
    __tablename__ = "role_templates"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    role: str
    department: str | None = None
    description: str | None = None
    interview_rounds: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON))
    created_at: datetime = timestamp_field()
    updated_at: datetime = timestamp_field()


class AuditEventRow(SQLModel, table=True):
    __tablename__ = "audit_events"

    id: int | None = Field(default=None, primary_key=True)
    event_type: str = Field(index=True)
    entity_type: str
    entity_id: str
    actor: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = timestamp_field()


class SyncJobRow(SQLModel, table=True):
    __tablename__ = "sync_jobs"
    __table_args__ = (UniqueConstraint("provider", "external_id"),)

    id: int | None = Field(default=None, primary_key=True)
    provider: str = Field(index=True)
    external_id: str = Field(index=True)
    status: SyncStatus = Field(index=True)
    error_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = timestamp_field()
    updated_at: datetime = timestamp_field()
