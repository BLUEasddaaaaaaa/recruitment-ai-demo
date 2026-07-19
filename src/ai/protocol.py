from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from src.domain.models import CandidateDraft, FeedbackClassification


class AIUsage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0)


class CandidateExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    draft: CandidateDraft
    usage: AIUsage


class FeedbackClassificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    classification: FeedbackClassification
    usage: AIUsage


class AIProvider(Protocol):
    def extract_candidate(
        self, resume_text: str, hr_notes: str, images: list[bytes] | tuple[bytes, ...]
    ) -> CandidateExtractionResult: ...

    def classify_feedback(self, text: str) -> FeedbackClassificationResult: ...
