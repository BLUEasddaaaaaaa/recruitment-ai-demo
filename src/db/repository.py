import json
import re
from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, NoReturn

from sqlalchemy import func, or_
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine, select

from src.db.models import (
    ApplicationRow,
    AuditEventRow,
    CandidateRow,
    InterviewRoundRow,
    RoleTemplateRow,
    SyncJobRow,
    utc_now,
)
from src.domain.models import (
    ApplicationStatus,
    CandidateConfirmed,
    InterviewInput,
    InterviewOutcome,
    RoleTemplate,
    SyncStatus,
)


class RepositoryError(RuntimeError):
    """Base class for persistence contract errors."""


class NotFoundError(RepositoryError):
    """Raised when a requested entity does not exist."""


class ValidationError(RepositoryError):
    """Raised when repository input violates a persistence invariant."""


@dataclass(frozen=True)
class DashboardAggregates:
    application_status_counts: dict[str, int]
    sync_failure_count: int


class RepositoryTransaction(AbstractContextManager["RepositoryTransaction"]):
    """A caller-controlled unit of work for composing atomic repository writes."""

    def __init__(self, repository: "Repository") -> None:
        self.repository = repository
        self.session = Session(repository.engine, expire_on_commit=False)

    def __enter__(self) -> "RepositoryTransaction":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        try:
            if exc_type is None:
                self.session.commit()
            else:
                self.session.rollback()
        except Exception:
            self.session.rollback()
            raise
        finally:
            self.session.close()
        return False

    def _add(self, row: Any) -> Any:
        self.session.add(row)
        self.session.flush()
        self.session.refresh(row)
        return row

    def create_candidate(self, candidate: CandidateConfirmed) -> CandidateRow:
        return self._add(self.repository._candidate_row(candidate))

    def get_candidate(self, candidate_id: int) -> CandidateRow:
        row = self.session.get(CandidateRow, candidate_id)
        if row is None:
            self.repository._not_found("candidate", candidate_id)
        return row

    def has_application_for_role(self, candidate_id: int, role: str) -> bool:
        statement = select(ApplicationRow.id).where(
            ApplicationRow.candidate_id == candidate_id,
            func.lower(ApplicationRow.role) == role.strip().lower(),
        )
        return self.session.exec(statement).first() is not None

    def create_application(
        self,
        candidate_id: int,
        *,
        role: str,
        department: str | None = None,
        status: ApplicationStatus = ApplicationStatus.NEW,
    ) -> ApplicationRow:
        return self._add(
            self.repository._application_row(
                self.session, candidate_id, role=role, department=department, status=status
            )
        )

    def append_audit_event(
        self,
        event_type: str,
        *,
        entity_type: str,
        entity_id: str,
        actor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditEventRow:
        return self._add(
            self.repository._audit_event_row(
                event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor=actor,
                payload=payload,
            )
        )

    def upsert_sync_job(
        self,
        provider: str,
        external_id: str,
        *,
        status: SyncStatus | str,
        error_message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> SyncJobRow:
        return self.repository._upsert_sync_job_in_session(
            self.session,
            provider,
            external_id,
            status=status,
            error_message=error_message,
            payload=payload,
        )


class Repository:
    def __init__(self, database_url: str) -> None:
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(database_url, connect_args=connect_args)
        SQLModel.metadata.create_all(self.engine)

    def transaction(self) -> RepositoryTransaction:
        return RepositoryTransaction(self)

    @staticmethod
    def _not_found(entity: str, entity_id: int) -> NoReturn:
        raise NotFoundError(f"{entity} {entity_id} was not found")

    @staticmethod
    def _required(value: str, field_name: str) -> str:
        value = value.strip()
        if not value:
            raise ValidationError(f"{field_name} must not be blank")
        return value

    @staticmethod
    def _application_status(status: ApplicationStatus | str) -> ApplicationStatus:
        try:
            return ApplicationStatus(status)
        except (TypeError, ValueError) as error:
            raise ValidationError(f"invalid application status: {status!r}") from error

    @staticmethod
    def _interview_outcome(outcome: InterviewOutcome | str) -> InterviewOutcome:
        try:
            return InterviewOutcome(outcome)
        except (TypeError, ValueError) as error:
            raise ValidationError(f"invalid interview outcome: {outcome!r}") from error

    @staticmethod
    def _sync_status(status: SyncStatus | str) -> SyncStatus:
        try:
            return SyncStatus(status)
        except (TypeError, ValueError) as error:
            raise ValidationError(f"invalid sync status: {status!r}") from error

    @staticmethod
    def _ensure_json(value: Any, field_name: str) -> Any:
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValidationError(
                f"{field_name} must contain only JSON-compatible values"
            ) from error
        return value

    @staticmethod
    def _normalize_phone(phone: str | None) -> str | None:
        if not phone:
            return None
        normalized = re.sub(r"[^0-9+]", "", phone)
        return normalized or None

    @staticmethod
    def _normalize_email(email: str | None) -> str | None:
        return email.strip().casefold() if email and email.strip() else None

    @staticmethod
    def _commit(session: Session, row: Any) -> Any:
        try:
            session.add(row)
            session.commit()
            session.refresh(row)
            return row
        except Exception:
            session.rollback()
            raise

    def _candidate_row(self, candidate: CandidateConfirmed) -> CandidateRow:
        name = self._required(candidate.name, "name")
        values = candidate.model_dump(mode="python")
        values["field_sources"] = {
            field: evidence.model_dump(mode="json")
            for field, evidence in candidate.field_sources.items()
        }
        values["name"] = name
        values["phone_normalized"] = self._normalize_phone(candidate.phone)
        values["email_normalized"] = self._normalize_email(candidate.email)
        for field_name in (
            "education",
            "work_experience",
            "internship_experience",
            "project_experience",
            "skills",
            "field_sources",
            "ai_metadata",
        ):
            self._ensure_json(values[field_name], field_name)
        return CandidateRow(**values)

    def create_candidate(self, candidate: CandidateConfirmed) -> CandidateRow:
        with self.transaction() as transaction:
            return transaction.create_candidate(candidate)

    def _application_row(
        self,
        session: Session,
        candidate_id: int,
        *,
        role: str,
        department: str | None,
        status: ApplicationStatus | str,
    ) -> ApplicationRow:
        role = self._required(role, "role")
        if session.get(CandidateRow, candidate_id) is None:
            self._not_found("candidate", candidate_id)
        return ApplicationRow(
            candidate_id=candidate_id,
            role=role,
            department=department.strip() if department else None,
            status=self._application_status(status),
        )

    def list_candidates(self) -> list[CandidateRow]:
        with Session(self.engine) as session:
            return list(session.exec(select(CandidateRow).order_by(CandidateRow.id)).all())

    def get_candidate(self, candidate_id: int) -> CandidateRow:
        with Session(self.engine) as session:
            row = session.get(CandidateRow, candidate_id)
            if row is None:
                self._not_found("candidate", candidate_id)
            return row

    def create_application(
        self,
        candidate_id: int,
        *,
        role: str,
        department: str | None = None,
        status: ApplicationStatus = ApplicationStatus.NEW,
    ) -> ApplicationRow:
        with self.transaction() as transaction:
            return transaction.create_application(
                candidate_id, role=role, department=department, status=status
            )

    def get_application(self, application_id: int) -> ApplicationRow:
        with Session(self.engine) as session:
            row = session.get(ApplicationRow, application_id)
            if row is None:
                self._not_found("application", application_id)
            return row

    def list_applications(self, candidate_id: int | None = None) -> list[ApplicationRow]:
        statement = select(ApplicationRow)
        if candidate_id is not None:
            statement = statement.where(ApplicationRow.candidate_id == candidate_id)
        with Session(self.engine) as session:
            return list(session.exec(statement.order_by(ApplicationRow.id)).all())

    def append_interview(self, application_id: int, interview: InterviewInput) -> InterviewRoundRow:
        round_name = self._required(interview.round_name, "round_name")
        with Session(self.engine) as session:
            if session.get(ApplicationRow, application_id) is None:
                self._not_found("application", application_id)
            row = InterviewRoundRow(
                application_id=application_id,
                round_name=round_name,
                interviewer=interview.interviewer,
                scheduled_at=interview.scheduled_at,
                outcome=self._interview_outcome(interview.outcome),
                notes=interview.notes,
                feedback=interview.feedback.model_dump(mode="json") if interview.feedback else None,
                metadata_json=interview.metadata,
            )
            self._ensure_json(row.feedback, "feedback")
            self._ensure_json(row.metadata_json, "metadata")
            return self._commit(session, row)

    def list_interviews(self, application_id: int) -> list[InterviewRoundRow]:
        with Session(self.engine) as session:
            statement = (
                select(InterviewRoundRow)
                .where(InterviewRoundRow.application_id == application_id)
                .order_by(InterviewRoundRow.created_at, InterviewRoundRow.id)
            )
            return list(session.exec(statement).all())

    def find_duplicate_candidates(
        self, *, phone: str | None = None, email: str | None = None
    ) -> list[CandidateRow]:
        phone_normalized = self._normalize_phone(phone)
        email_normalized = self._normalize_email(email)
        predicates = []
        if phone_normalized:
            predicates.append(CandidateRow.phone_normalized == phone_normalized)
        if email_normalized:
            predicates.append(CandidateRow.email_normalized == email_normalized)
        if not predicates:
            return []
        with Session(self.engine) as session:
            statement = select(CandidateRow).where(or_(*predicates)).order_by(CandidateRow.id)
            return list(session.exec(statement).all())

    def save_role_template(self, template: RoleTemplate) -> RoleTemplateRow:
        self._ensure_json(template.metadata, "metadata")
        self._ensure_json(template.interview_rounds, "interview_rounds")
        if not template.interview_rounds or any(
            not round_name.strip() for round_name in template.interview_rounds
        ):
            raise ValidationError("interview_rounds must contain non-blank stage names")
        row = RoleTemplateRow(
            name=self._required(template.name, "name"),
            role=self._required(template.role, "role"),
            department=template.department,
            description=template.description,
            interview_rounds=[round_name.strip() for round_name in template.interview_rounds],
            metadata_json=template.metadata,
        )
        with Session(self.engine) as session:
            return self._commit(session, row)

    def instantiate_template(self, template_id: int, candidate_id: int) -> ApplicationRow:
        with Session(self.engine) as session:
            template = session.get(RoleTemplateRow, template_id)
            if template is None:
                self._not_found("role template", template_id)
            if session.get(CandidateRow, candidate_id) is None:
                self._not_found("candidate", candidate_id)
            try:
                application = ApplicationRow(
                    candidate_id=candidate_id,
                    role=self._required(template.role, "role"),
                    department=template.department,
                    template_id=template.id,
                )
                session.add(application)
                session.flush()
                for round_name in template.interview_rounds:
                    session.add(
                        InterviewRoundRow(
                            application_id=application.id,
                            round_name=self._required(round_name, "round_name"),
                        )
                    )
                session.commit()
                session.refresh(application)
                return application
            except Exception:
                session.rollback()
                raise

    def update_application_status(
        self, application_id: int, status: ApplicationStatus
    ) -> ApplicationRow:
        with Session(self.engine) as session:
            row = session.get(ApplicationRow, application_id)
            if row is None:
                self._not_found("application", application_id)
            row.status = self._application_status(status)
            row.updated_at = utc_now()
            return self._commit(session, row)

    def _audit_event_row(
        self,
        event_type: str,
        *,
        entity_type: str,
        entity_id: str,
        actor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditEventRow:
        payload = payload or {}
        self._ensure_json(payload, "payload")
        return AuditEventRow(
            event_type=self._required(event_type, "event_type"),
            entity_type=self._required(entity_type, "entity_type"),
            entity_id=self._required(entity_id, "entity_id"),
            actor=actor,
            payload=payload,
        )

    def append_audit_event(
        self,
        event_type: str,
        *,
        entity_type: str,
        entity_id: str,
        actor: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AuditEventRow:
        with self.transaction() as transaction:
            return transaction.append_audit_event(
                event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor=actor,
                payload=payload,
            )

    def list_audit_events(self) -> list[AuditEventRow]:
        with Session(self.engine) as session:
            statement = select(AuditEventRow).order_by(AuditEventRow.created_at, AuditEventRow.id)
            return list(session.exec(statement).all())

    def upsert_sync_job(
        self,
        provider: str,
        external_id: str,
        *,
        status: SyncStatus | str,
        error_message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> SyncJobRow:
        with self.transaction() as transaction:
            return transaction.upsert_sync_job(
                provider,
                external_id,
                status=status,
                error_message=error_message,
                payload=payload,
            )

    def list_sync_jobs(self) -> list[SyncJobRow]:
        with Session(self.engine) as session:
            return list(session.exec(select(SyncJobRow).order_by(SyncJobRow.id)).all())

    def delete_candidate(self, candidate_id: int) -> None:
        with Session(self.engine) as session:
            candidate = session.get(CandidateRow, candidate_id)
            if candidate is None:
                self._not_found("candidate", candidate_id)
            applications = list(
                session.exec(
                    select(ApplicationRow).where(ApplicationRow.candidate_id == candidate_id)
                ).all()
            )
            for application in applications:
                for interview in list(
                    session.exec(
                        select(InterviewRoundRow).where(
                            InterviewRoundRow.application_id == application.id
                        )
                    ).all()
                ):
                    session.delete(interview)
                session.delete(application)
            session.delete(candidate)
            session.commit()

    def _upsert_sync_job_in_session(
        self,
        session: Session,
        provider: str,
        external_id: str,
        *,
        status: SyncStatus | str,
        error_message: str | None,
        payload: dict[str, Any] | None,
    ) -> SyncJobRow:
        provider = self._required(provider, "provider")
        external_id = self._required(external_id, "external_id")
        status = self._sync_status(self._required(status, "status"))
        payload = payload or {}
        self._ensure_json(payload, "payload")
        now = utc_now()
        if self.engine.dialect.name == "sqlite":
            statement = sqlite_insert(SyncJobRow).values(
                provider=provider,
                external_id=external_id,
                status=status,
                error_message=error_message,
                payload=payload,
                created_at=now,
                updated_at=now,
            )
            statement = statement.on_conflict_do_update(
                index_elements=["provider", "external_id"],
                set_={
                    "status": status,
                    "error_message": error_message,
                    "payload": payload,
                    "updated_at": now,
                },
            )
            session.exec(statement)
            row = session.exec(
                select(SyncJobRow).where(
                    SyncJobRow.provider == provider,
                    SyncJobRow.external_id == external_id,
                )
            ).one()
            return row

        statement = select(SyncJobRow).where(
            SyncJobRow.provider == provider, SyncJobRow.external_id == external_id
        )
        row = session.exec(statement).one_or_none()
        if row is None:
            row = SyncJobRow(provider=provider, external_id=external_id, status=status)
        row.status = status
        row.error_message = error_message
        row.payload = payload
        row.updated_at = now
        session.add(row)
        session.flush()
        session.refresh(row)
        return row

    def dashboard_aggregates(self) -> DashboardAggregates:
        with Session(self.engine) as session:
            status_rows: Sequence[tuple[ApplicationStatus, int]] = session.exec(
                select(ApplicationRow.status, func.count(ApplicationRow.id)).group_by(
                    ApplicationRow.status
                )
            ).all()
            failed = session.exec(
                select(func.count(SyncJobRow.id)).where(
                    SyncJobRow.status.in_([SyncStatus.RETRYING, SyncStatus.DEAD_LETTER])
                )
            ).one()
        return DashboardAggregates(
            application_status_counts={status.value: count for status, count in status_rows},
            sync_failure_count=failed,
        )
