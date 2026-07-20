from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ResumeParseRequest(BaseModel):
    """Payload sent by the React resume-entry page.

    - `text` is kept for plain-text paste / backwards compatibility.
    - `fileContent` is a base64 encoded file (PDF/DOCX/TXT) for binary parsing.
    """

    text: str = ""
    fileName: Optional[str] = None
    fileContent: Optional[str] = None
    role: Optional[str] = None


class CandidateCreate(BaseModel):
    """Flat payload sent by the React resume-entry confirm step.

    Mirrors the existing front-end contract (name / phone / email / hrName /
    jobTitle / department / status / resumeText / parsedInfo ...). Extra parsed
    fields are accepted so the Python backend can persist structured data.
    """

    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    hrName: Optional[str] = None
    jobTitle: Optional[str] = None
    department: Optional[str] = None
    status: str = "screening"
    currentRound: int = 0
    latestConclusion: Optional[str] = None
    resumeFileName: Optional[str] = None
    resumeText: Optional[str] = None
    interviews: list[Any] = Field(default_factory=list)
    # Parsed structured fields
    education: Optional[str] = None
    experience: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    expectedSalary: Optional[str] = None
    availability: Optional[str] = None
    sourceChannel: Optional[str] = None
    confidence: dict[str, Any] = Field(default_factory=dict)


class StatusUpdate(BaseModel):
    status: str
    latestConclusion: Optional[str] = None


class InterviewCreate(BaseModel):
    round: int = 1
    interviewer: Optional[str] = None
    date: Optional[str] = None
    result: Literal["pass", "fail", "pending"] = "pending"
    feedback: Optional[str] = None
