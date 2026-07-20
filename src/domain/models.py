from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator


def _require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value


AwareDateTime = Annotated[datetime, AfterValidator(_require_aware_datetime)]


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FieldEvidence(DomainModel):
    source: str
    quote: str
    confidence: float = Field(ge=0, le=1)


class CandidateDraft(DomainModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    current_city: str | None = None
    education: list[dict[str, Any]] = Field(default_factory=list)
    work_experience: list[dict[str, Any]] = Field(default_factory=list)
    internship_experience: list[dict[str, Any]] = Field(default_factory=list)
    project_experience: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    expected_salary: str | None = None
    availability: str | None = None
    source_channel: str | None = None
    hr_notes: str | None = None
    field_sources: dict[str, FieldEvidence] = Field(default_factory=dict)
    ai_model: str | None = None
    ai_request_id: str | None = None
    ai_generated_at: AwareDateTime | None = None
    ai_metadata: dict[str, Any] = Field(default_factory=dict)


class CandidateConfirmed(CandidateDraft):
    name: str
    confirmed_by: str | None = None
    confirmed_at: AwareDateTime | None = None
    confirmation_notes: str | None = None


class ApplicationStatus(StrEnum):
    NEW = "new"
    SCREENING = "screening"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class SyncStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class FeedbackDecision(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    HOLD = "hold"
    UNCLEAR = "unclear"


class FeedbackClassification(DomainModel):
    decision: FeedbackDecision
    reason: str
    evidence_quote: str | None = None
    confidence: float = Field(ge=0, le=1)
    requires_human_confirmation: bool = True


class InterviewOutcome(StrEnum):
    PENDING = "pending"
    PASS = "pass"
    FAIL = "fail"
    HOLD = "hold"
    CANCELLED = "cancelled"


class InterviewInput(DomainModel):
    round_name: str
    interviewer: str | None = None
    scheduled_at: AwareDateTime | None = None
    outcome: InterviewOutcome = InterviewOutcome.PENDING
    notes: str | None = None
    feedback: FeedbackClassification | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoleTemplate(DomainModel):
    name: str
    role: str
    department: str | None = None
    description: str | None = None
    interview_rounds: list[str] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("interview_rounds")
    @classmethod
    def validate_interview_rounds(cls, rounds: list[str]) -> list[str]:
        normalized = [round_name.strip() for round_name in rounds]
        if any(not round_name for round_name in normalized):
            raise ValueError("interview_rounds must not contain blank stage names")
        return normalized
