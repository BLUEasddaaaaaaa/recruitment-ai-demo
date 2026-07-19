from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from threading import RLock
from types import MappingProxyType
from typing import Any, Callable, Mapping

from pydantic import ConfigDict, ValidationError as PydanticValidationError

from src.ai.protocol import AIProvider, AIUsage
from src.db.models import ApplicationRow, CandidateRow
from src.db.repository import Repository
from src.documents.extract_text import UnsupportedDocument, extract_document
from src.domain.models import CandidateConfirmed, CandidateDraft, FieldEvidence, SyncStatus


class IntakeError(RuntimeError):
    """Base class for safe, user-facing intake failures."""


class IntakeValidationError(IntakeError):
    pass


class DraftNotFoundError(IntakeError):
    pass


class DraftExpiredError(IntakeError):
    pass


class DraftConsumedError(IntakeError):
    pass


class ConfirmationChoice(StrEnum):
    CREATE_NEW = "create_new"
    REUSE_DUPLICATE = "reuse_duplicate"
    NO_DUPLICATE = "no_duplicate"


class FrozenFieldEvidence(FieldEvidence):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FrozenCandidateDraft(CandidateDraft):
    model_config = ConfigDict(extra="forbid", frozen=True)
    field_sources: dict[str, FrozenFieldEvidence]

    def model_post_init(self, context: Any) -> None:
        for field_name in type(self).model_fields:
            object.__setattr__(self, field_name, _deep_freeze(getattr(self, field_name)))


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    filename: str
    mime_type: str
    sha256: str
    attachment_reference: str


@dataclass(frozen=True, slots=True)
class DuplicateHint:
    candidate_id: int
    display_name: str
    matched_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IntakeConflict:
    field_name: str
    resume_value: str
    resume_source: str
    note_value: str
    note_source: str


@dataclass(frozen=True, slots=True)
class PreparedIntake:
    token: str
    draft: FrozenCandidateDraft
    role: str
    department: str | None
    document: DocumentMetadata
    duplicate_hints: tuple[DuplicateHint, ...]
    conflicts: tuple[IntakeConflict, ...]
    usage: AIUsage
    expires_at: datetime


@dataclass(slots=True)
class _StoredDraft:
    prepared: PreparedIntake
    confirmed_result: tuple[CandidateRow, ApplicationRow] | None = None
    idempotency_key: str | None = None
    consumed: bool = False


class IntakeService:
    def __init__(
        self,
        repository: Repository,
        ai_provider: AIProvider,
        *,
        clock: Callable[[], datetime] | None = None,
        ttl: timedelta = timedelta(minutes=30),
    ) -> None:
        if ttl <= timedelta(0):
            raise ValueError("ttl must be positive")
        self._repository = repository
        self._ai_provider = ai_provider
        self._clock = clock or (lambda: datetime.now(UTC))
        self._ttl = ttl
        self._drafts: dict[str, _StoredDraft] = {}
        self._lock = RLock()

    def prepare_draft(
        self,
        filename: str,
        content: bytes,
        hr_notes: str,
        role: str,
        *,
        department: str | None = None,
    ) -> PreparedIntake:
        role = role.strip()
        if not role:
            raise IntakeValidationError("role must not be blank")
        department = department.strip() if department and department.strip() else None
        try:
            document = extract_document(filename, content)
        except UnsupportedDocument as error:
            raise IntakeValidationError(f"document could not be processed: {error}") from error

        result = self._ai_provider.extract_candidate(
            document.text, hr_notes, list(document.image_bytes)
        )
        draft = FrozenCandidateDraft.model_validate(result.draft.model_dump(mode="python"))
        hints = self._duplicate_hints(draft)
        now = self._aware_now()
        digest = hashlib.sha256(content).hexdigest()
        token = secrets.token_urlsafe(32)
        prepared = PreparedIntake(
            token=token,
            draft=draft,
            role=role,
            department=department,
            document=DocumentMetadata(
                filename=document.filename,
                mime_type=document.mime_type,
                sha256=digest,
                attachment_reference=f"sha256:{digest}",
            ),
            duplicate_hints=hints,
            conflicts=self._find_conflicts(draft, hr_notes),
            usage=result.usage,
            expires_at=now + self._ttl,
        )
        with self._lock:
            self._drafts[token] = _StoredDraft(prepared)
        return prepared

    def confirm(
        self,
        token: str,
        *,
        confirmed_by: str,
        choice: ConfirmationChoice | str | None = None,
        confirmed: CandidateDraft | CandidateConfirmed | None = None,
        selected_candidate_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> tuple[CandidateRow, ApplicationRow]:
        actor = confirmed_by.strip()
        if not actor:
            raise IntakeValidationError("confirmed_by must not be blank")
        try:
            duplicate_choice = ConfirmationChoice(choice) if choice is not None else None
        except ValueError as error:
            raise IntakeValidationError("invalid duplicate choice") from error
        if duplicate_choice is None:
            raise IntakeValidationError("duplicate choice is required")

        with self._lock:
            stored = self._drafts.get(token)
            if stored is None:
                raise DraftNotFoundError("intake draft was not found")
            if stored.confirmed_result is not None and stored.idempotency_key == idempotency_key:
                return stored.confirmed_result
            if stored.consumed:
                raise DraftConsumedError("intake draft has already been consumed")
            if self._aware_now() >= stored.prepared.expires_at:
                raise DraftExpiredError("intake draft has expired")

            prepared = stored.prepared
            final = self._confirmed_candidate(prepared, confirmed, actor)
            selected_id = self._validate_duplicate_choice(
                prepared, duplicate_choice, selected_candidate_id
            )
            result = self._persist_confirmation(
                prepared, final, actor, duplicate_choice, selected_id
            )
            stored.confirmed_result = result
            stored.idempotency_key = idempotency_key
            stored.consumed = True
            return result

    def _persist_confirmation(
        self,
        prepared: PreparedIntake,
        final: CandidateConfirmed,
        actor: str,
        choice: ConfirmationChoice,
        selected_candidate_id: int | None,
    ) -> tuple[CandidateRow, ApplicationRow]:
        changed_fields = sorted(
            field
            for field in CandidateDraft.model_fields
            if field not in {"hr_notes", "field_sources", "ai_metadata"}
            and _deep_thaw(getattr(prepared.draft, field)) != _deep_thaw(getattr(final, field))
        )
        source_labels = sorted(
            {evidence.source for evidence in prepared.draft.field_sources.values()}
        )
        with self._repository.transaction() as transaction:
            if choice == ConfirmationChoice.REUSE_DUPLICATE:
                assert selected_candidate_id is not None
                candidate = transaction.get_candidate(selected_candidate_id)
                if transaction.has_application_for_role(candidate.id, prepared.role):
                    raise IntakeValidationError(
                        "selected candidate already has an application for this role"
                    )
            else:
                candidate = transaction.create_candidate(final)
            application = transaction.create_application(
                candidate.id, role=prepared.role, department=prepared.department
            )
            transaction.append_audit_event(
                "candidate_intake_confirmed",
                entity_type="application",
                entity_id=str(application.id),
                actor=actor,
                payload={
                    "candidate_id": candidate.id,
                    "choice": choice.value,
                    "changed_fields": changed_fields,
                    "evidence_sources": source_labels,
                    "conflict_fields": [conflict.field_name for conflict in prepared.conflicts],
                    "ai_usage": prepared.usage.model_dump(mode="json"),
                },
            )
            transaction.upsert_sync_job(
                "candidate_docs",
                f"intake:{prepared.token}:candidate-docs",
                status=SyncStatus.PENDING,
                payload={
                    "candidate_id": candidate.id,
                    "application_id": application.id,
                    "document": {
                        "display_name": _safe_display_name(prepared.document.mime_type),
                        "mime_type": prepared.document.mime_type,
                        "sha256": prepared.document.sha256,
                        "attachment_id": prepared.document.attachment_reference,
                    },
                },
            )
            transaction.upsert_sync_job(
                "department_notification",
                f"intake:{prepared.token}:department-notification",
                status=SyncStatus.PENDING,
                payload={"candidate_id": candidate.id, "application_id": application.id},
            )
        return candidate, application

    def _confirmed_candidate(
        self,
        prepared: PreparedIntake,
        edited: CandidateDraft | CandidateConfirmed | None,
        actor: str,
    ) -> CandidateConfirmed:
        source = edited or prepared.draft
        values = {
            field_name: _deep_thaw(getattr(source, field_name))
            for field_name in CandidateDraft.model_fields
        }
        metadata = dict(values.get("ai_metadata") or {})
        metadata.update(
            {
                "usage": prepared.usage.model_dump(mode="json"),
                "intake": {
                    "document": {
                        "filename": prepared.document.filename,
                        "mime_type": prepared.document.mime_type,
                        "sha256": prepared.document.sha256,
                        "attachment_reference": prepared.document.attachment_reference,
                    }
                },
            }
        )
        values.update(
            confirmed_by=actor,
            confirmed_at=self._aware_now(),
            ai_metadata=metadata,
        )
        try:
            candidate = CandidateConfirmed.model_validate(values)
        except PydanticValidationError as error:
            raise IntakeValidationError(f"confirmed candidate is invalid: {error}") from error
        if not candidate.name.strip():
            raise IntakeValidationError("confirmed candidate name must not be blank")
        return candidate

    def _validate_duplicate_choice(
        self,
        prepared: PreparedIntake,
        choice: ConfirmationChoice,
        selected_candidate_id: int | None,
    ) -> int | None:
        if choice == ConfirmationChoice.REUSE_DUPLICATE:
            hinted = {hint.candidate_id for hint in prepared.duplicate_hints}
            if selected_candidate_id not in hinted:
                raise IntakeValidationError(
                    "selected_candidate_id must be one of the duplicate hints"
                )
            return selected_candidate_id
        if selected_candidate_id is not None:
            raise IntakeValidationError(
                "selected_candidate_id is only valid when reusing a duplicate"
            )
        if choice == ConfirmationChoice.NO_DUPLICATE and prepared.duplicate_hints:
            raise IntakeValidationError("use create_new when duplicate hints are present")
        return None

    def _duplicate_hints(self, draft: CandidateDraft) -> tuple[DuplicateHint, ...]:
        rows = self._repository.find_duplicate_candidates(phone=draft.phone, email=draft.email)
        hints = []
        for row in rows:
            matched = []
            if (
                draft.phone
                and self._repository._normalize_phone(draft.phone) == row.phone_normalized
            ):
                matched.append("phone")
            if (
                draft.email
                and self._repository._normalize_email(draft.email) == row.email_normalized
            ):
                matched.append("email")
            hints.append(DuplicateHint(row.id, row.name, tuple(matched)))
        return tuple(hints)

    @staticmethod
    def _find_conflicts(draft: CandidateDraft, hr_notes: str) -> tuple[IntakeConflict, ...]:
        conflicts: list[IntakeConflict] = []
        availability = re.search(
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d+)周到岗|随时到岗)", hr_notes
        )
        evidence = draft.field_sources.get("availability")
        if availability and draft.availability and availability.group(1) != draft.availability:
            conflicts.append(
                IntakeConflict(
                    field_name="availability",
                    resume_value=draft.availability,
                    resume_source=evidence.source if evidence else "resume_text",
                    note_value=availability.group(1),
                    note_source="boss_note",
                )
            )
        return tuple(conflicts)

    def _aware_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must return a timezone-aware datetime")
        return value


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _deep_thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_deep_thaw(item) for item in value]
    return value


def _safe_display_name(mime_type: str) -> str:
    extensions = {
        "text/plain": ".txt",
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "image/png": ".png",
        "image/jpeg": ".jpg",
    }
    return f"resume{extensions.get(mime_type, '')}"
