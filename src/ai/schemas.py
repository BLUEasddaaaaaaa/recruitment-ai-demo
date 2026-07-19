from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.domain.models import FeedbackDecision


class AIOutputModel(BaseModel):
    """Strict base for data that may be populated by an untrusted model."""

    model_config = ConfigDict(extra="forbid")


class CandidateFieldEvidenceOutput(AIOutputModel):
    field_name: Literal[
        "name",
        "phone",
        "email",
        "current_city",
        "education",
        "work_experience",
        "internship_experience",
        "project_experience",
        "skills",
        "expected_salary",
        "availability",
        "source_channel",
    ]
    source: Literal["resume_text", "boss_note", "resume_image"]
    quote: str
    confidence: float = Field(ge=0, le=1)


class EducationOutput(AIOutputModel):
    school: str | None = None
    degree: str | None = None
    major: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class WorkExperienceOutput(AIOutputModel):
    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: list[str] = Field(default_factory=list)


class InternshipExperienceOutput(AIOutputModel):
    company: str | None = None
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: list[str] = Field(default_factory=list)


class ProjectExperienceOutput(AIOutputModel):
    name: str | None = None
    role: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: list[str] = Field(default_factory=list)


class CandidateExtractionOutput(AIOutputModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    current_city: str | None = None
    education: list[EducationOutput] = Field(default_factory=list)
    work_experience: list[WorkExperienceOutput] = Field(default_factory=list)
    internship_experience: list[InternshipExperienceOutput] = Field(default_factory=list)
    project_experience: list[ProjectExperienceOutput] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    expected_salary: str | None = None
    availability: str | None = None
    source_channel: str | None = None
    field_sources: list[CandidateFieldEvidenceOutput] = Field(default_factory=list)


class FeedbackClassificationOutput(AIOutputModel):
    decision: FeedbackDecision
    reason: str
    evidence_quote: str | None = None
    confidence: float = Field(ge=0, le=1)
