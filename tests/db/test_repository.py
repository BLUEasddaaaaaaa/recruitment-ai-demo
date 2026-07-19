from datetime import UTC, datetime

import pytest
from pydantic import ValidationError as PydanticValidationError

from src.db.repository import NotFoundError, Repository, ValidationError
from src.domain.models import (
    ApplicationStatus,
    CandidateConfirmed,
    InterviewInput,
    InterviewOutcome,
    RoleTemplate,
    SyncStatus,
)


@pytest.fixture
def repo(tmp_path) -> Repository:
    return Repository(f"sqlite:///{tmp_path}/test.db")


def test_candidate_can_have_multiple_applications_and_rounds(tmp_path) -> None:
    repo = Repository(f"sqlite:///{tmp_path}/test.db")
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓", phone="13800000000"))
    app_a = repo.create_application(candidate.id, role="后端开发", department="研发")
    app_b = repo.create_application(candidate.id, role="数据分析", department="产品")
    repo.append_interview(app_a.id, InterviewInput(round_name="技术初试", interviewer="王经理"))
    repo.append_interview(app_a.id, InterviewInput(round_name="技术复试", interviewer="陈总"))
    assert app_a.id != app_b.id
    assert [item.round_name for item in repo.list_interviews(app_a.id)] == [
        "技术初试",
        "技术复试",
    ]


def test_create_and_list_candidates_populates_utc_timestamps(repo: Repository) -> None:
    created = repo.create_candidate(
        CandidateConfirmed(name="林晓", email="lin@example.com", skills=["Python"])
    )

    assert repo.list_candidates() == [created]
    assert created.created_at.tzinfo == UTC
    assert created.updated_at.tzinfo == UTC
    assert created.skills == ["Python"]


def test_application_creation_listing_and_lookup(repo: Repository) -> None:
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓"))
    first = repo.create_application(candidate.id, role="后端开发", department="研发")
    second = repo.create_application(candidate.id, role="数据分析", department="产品")

    assert repo.get_application(first.id) == first
    assert repo.list_applications(candidate.id) == [first, second]
    assert first.status == ApplicationStatus.NEW


def test_missing_parent_or_record_raises_clear_errors(repo: Repository) -> None:
    with pytest.raises(NotFoundError, match="candidate"):
        repo.create_application(999, role="后端开发", department="研发")
    with pytest.raises(NotFoundError, match="application"):
        repo.get_application(999)
    with pytest.raises(NotFoundError, match="application"):
        repo.append_interview(999, InterviewInput(round_name="初试"))


def test_interviews_are_append_only_ordered_and_capture_outcome(repo: Repository) -> None:
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓"))
    application = repo.create_application(candidate.id, role="后端开发", department="研发")
    first = repo.append_interview(
        application.id,
        InterviewInput(
            round_name="初试",
            interviewer="王经理",
            outcome=InterviewOutcome.PASS,
            notes="基础扎实",
        ),
    )
    second = repo.append_interview(application.id, InterviewInput(round_name="复试"))

    assert repo.list_interviews(application.id) == [first, second]
    assert first.outcome == InterviewOutcome.PASS
    assert first.created_at.tzinfo == UTC


def test_find_duplicate_candidates_uses_exact_normalized_phone_or_email(repo: Repository) -> None:
    by_phone = repo.create_candidate(CandidateConfirmed(name="甲", phone="138 0000 0000"))
    by_email = repo.create_candidate(CandidateConfirmed(name="乙", email="USER@Example.com"))
    repo.create_candidate(CandidateConfirmed(name="丙", phone="13900000000"))

    phone_matches = repo.find_duplicate_candidates(phone="13800000000")
    email_matches = repo.find_duplicate_candidates(email=" user@example.com ")

    assert [item.id for item in phone_matches] == [by_phone.id]
    assert [item.id for item in email_matches] == [by_email.id]
    assert repo.find_duplicate_candidates() == []


def test_role_template_can_be_saved_and_instantiated(repo: Repository) -> None:
    template = repo.save_role_template(
        RoleTemplate(
            name="研发通用",
            role="后端开发",
            department="研发",
            interview_rounds=["技术初试", "技术复试"],
        )
    )
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓"))

    application = repo.instantiate_template(template.id, candidate.id)

    assert application.role == "后端开发"
    assert [item.round_name for item in repo.list_interviews(application.id)] == [
        "技术初试",
        "技术复试",
    ]


def test_save_template_revalidates_constructed_domain_data(repo: Repository) -> None:
    invalid = RoleTemplate.model_construct(
        name="损坏模板", role="后端开发", interview_rounds=["初试", ""], metadata={}
    )

    with pytest.raises(ValidationError, match="interview_rounds"):
        repo.save_role_template(invalid)


def test_update_application_status_refreshes_timestamp(repo: Repository) -> None:
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓"))
    application = repo.create_application(candidate.id, role="后端开发")
    previous = application.updated_at

    updated = repo.update_application_status(application.id, ApplicationStatus.INTERVIEWING)

    assert updated.status == ApplicationStatus.INTERVIEWING
    assert updated.updated_at >= previous


def test_audit_events_are_append_only_and_ordered(repo: Repository) -> None:
    first = repo.append_audit_event("candidate.created", entity_type="candidate", entity_id="1")
    second = repo.append_audit_event(
        "application.status_changed",
        entity_type="application",
        entity_id="2",
        payload={"status": "interviewing"},
    )

    assert repo.list_audit_events() == [first, second]
    assert second.payload == {"status": "interviewing"}


def test_upsert_sync_job_creates_then_updates_single_external_job(repo: Repository) -> None:
    created = repo.upsert_sync_job(
        "ats", "job-1", status=SyncStatus.RETRYING, error_message="timeout", payload={"attempt": 1}
    )
    updated = repo.upsert_sync_job(
        "ats", "job-1", status=SyncStatus.SUCCEEDED, payload={"attempt": 2}
    )

    assert updated.id == created.id
    assert updated.status == SyncStatus.SUCCEEDED
    assert updated.error_message is None
    assert updated.payload == {"attempt": 2}
    assert updated.updated_at >= created.updated_at


def test_dashboard_aggregates_statuses_and_sync_failures(repo: Repository) -> None:
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓"))
    interviewing = repo.create_application(candidate.id, role="后端开发")
    repo.create_application(candidate.id, role="数据分析")
    repo.update_application_status(interviewing.id, ApplicationStatus.INTERVIEWING)
    repo.upsert_sync_job("ats", "retry-1", status=SyncStatus.RETRYING)
    repo.upsert_sync_job("ats", "dead-1", status=SyncStatus.DEAD_LETTER)
    repo.upsert_sync_job("ats", "ok-1", status=SyncStatus.SUCCEEDED)
    repo.upsert_sync_job("ats", "pending-1", status=SyncStatus.PENDING)

    aggregates = repo.dashboard_aggregates()

    assert aggregates.application_status_counts == {"new": 1, "interviewing": 1}
    assert aggregates.sync_failure_count == 2


def test_blank_required_values_are_rejected_without_partial_write(repo: Repository) -> None:
    with pytest.raises(ValidationError, match="name"):
        repo.create_candidate(CandidateConfirmed(name="   "))
    assert repo.list_candidates() == []


def test_explicit_datetime_is_preserved_as_aware_utc(repo: Repository) -> None:
    before = datetime.now(UTC)
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓", confirmed_at=before))
    assert candidate.confirmed_at == before


def test_transaction_rolls_back_all_writes_on_error(repo: Repository) -> None:
    with pytest.raises(ValidationError, match="role"):
        with repo.transaction() as transaction:
            candidate = transaction.create_candidate(CandidateConfirmed(name="林晓"))
            transaction.create_application(candidate.id, role="后端开发")
            transaction.append_audit_event(
                "candidate.created", entity_type="candidate", entity_id=str(candidate.id)
            )
            transaction.upsert_sync_job("ats", "candidate-1", status=SyncStatus.DEAD_LETTER)
            transaction.create_application(candidate.id, role="   ")

    assert repo.list_candidates() == []
    assert repo.list_applications() == []
    assert repo.list_audit_events() == []
    assert repo.dashboard_aggregates().sync_failure_count == 0


def test_transaction_commits_multiple_writes_atomically(repo: Repository) -> None:
    with repo.transaction() as transaction:
        candidate = transaction.create_candidate(CandidateConfirmed(name="林晓"))
        application = transaction.create_application(candidate.id, role="后端开发")
        audit = transaction.append_audit_event(
            "application.created", entity_type="application", entity_id=str(application.id)
        )
        transaction.upsert_sync_job("ats", "application-1", status=SyncStatus.DEAD_LETTER)

    assert repo.list_candidates() == [candidate]
    assert repo.list_applications() == [application]
    assert repo.list_audit_events() == [audit]
    assert repo.dashboard_aggregates().sync_failure_count == 1


@pytest.mark.parametrize("field", ["confirmed_at", "ai_generated_at"])
def test_candidate_rejects_naive_datetimes(field: str) -> None:
    with pytest.raises(PydanticValidationError, match="timezone-aware"):
        CandidateConfirmed(name="林晓", **{field: datetime.now()})


def test_interview_rejects_naive_scheduled_datetime() -> None:
    with pytest.raises(PydanticValidationError, match="timezone-aware"):
        InterviewInput(round_name="初试", scheduled_at=datetime.now())


def test_repository_rejects_non_json_metadata_before_sql(repo: Repository) -> None:
    with pytest.raises(ValidationError, match="JSON-compatible"):
        repo.create_candidate(CandidateConfirmed(name="林晓", ai_metadata={"bad": object()}))
    assert repo.list_candidates() == []


@pytest.mark.parametrize("rounds", [[], ["初试", "   "]])
def test_role_template_rejects_missing_or_blank_rounds(rounds: list[str]) -> None:
    with pytest.raises(PydanticValidationError, match="interview_rounds"):
        RoleTemplate(name="研发通用", role="后端开发", interview_rounds=rounds)


def test_runtime_status_values_are_validated(repo: Repository) -> None:
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓"))
    application = repo.create_application(candidate.id, role="后端开发")

    with pytest.raises(ValidationError, match="application status"):
        repo.update_application_status(application.id, "invented")  # type: ignore[arg-type]
    with pytest.raises(ValidationError, match="sync status"):
        repo.upsert_sync_job("ats", "job-1", status="invented")


def test_runtime_interview_outcome_is_validated(repo: Repository) -> None:
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓"))
    application = repo.create_application(candidate.id, role="后端开发")
    interview = InterviewInput.model_construct(round_name="初试", outcome="invented")

    with pytest.raises(ValidationError, match="interview outcome"):
        repo.append_interview(application.id, interview)


def test_repeated_sync_upsert_keeps_one_row(repo: Repository) -> None:
    first = repo.upsert_sync_job("ats", "job-1", status=SyncStatus.RETRYING)
    second = repo.upsert_sync_job("ats", "job-1", status=SyncStatus.SUCCEEDED)

    assert first.id == second.id
    assert repo.dashboard_aggregates().sync_failure_count == 0


@pytest.mark.parametrize("status", list(SyncStatus))
def test_sync_lifecycle_accepts_each_approved_status(repo: Repository, status: SyncStatus) -> None:
    job = repo.upsert_sync_job("ats", f"job-{status.value}", status=status)
    assert job.status == status


@pytest.mark.parametrize("status", ["failed", "running", "invented"])
def test_sync_lifecycle_rejects_unapproved_statuses(repo: Repository, status: str) -> None:
    with pytest.raises(ValidationError, match="sync status"):
        repo.upsert_sync_job("ats", "job-invalid", status=status)
