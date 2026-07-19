from datetime import UTC, datetime, timedelta
import json

import pytest

from src.ai.protocol import AIUsage, CandidateExtractionResult
from src.db.repository import Repository
from src.domain.models import CandidateConfirmed, CandidateDraft, FieldEvidence
from src.services.intake import (
    ConfirmationChoice,
    DraftConsumedError,
    DraftExpiredError,
    DraftNotFoundError,
    IntakeService,
    IntakeValidationError,
)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 7, 19, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


class Provider:
    def __init__(self, draft: CandidateDraft | None = None) -> None:
        self.draft = draft or CandidateDraft(
            name="张三",
            phone="138-0000-0000",
            email="ZHANG@example.com",
            availability="一个月到岗",
            field_sources={
                "name": FieldEvidence(source="resume_text", quote="姓名：张三", confidence=0.99),
                "availability": FieldEvidence(
                    source="resume_text", quote="一个月到岗", confidence=0.8
                ),
            },
        )

    def extract_candidate(self, resume_text, hr_notes, images):
        return CandidateExtractionResult(
            draft=self.draft,
            usage=AIUsage(input_tokens=11, output_tokens=7, total_tokens=18),
        )


@pytest.fixture
def repo(tmp_path):
    return Repository(f"sqlite:///{tmp_path / 'test.db'}")


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def intake(repo, clock):
    return IntakeService(repo, Provider(), clock=clock, ttl=timedelta(minutes=15))


@pytest.fixture
def resume_bytes():
    return "姓名：张三\n电话：138-0000-0000\n一个月到岗".encode()


def test_ai_draft_is_not_persisted_before_hr_confirmation(intake, repo, resume_bytes):
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "两周到岗", "后端开发")
    assert repo.list_candidates() == []
    candidate, application = intake.confirm(
        prepared.token, confirmed_by="hr_001", choice=ConfirmationChoice.NO_DUPLICATE
    )
    assert candidate.confirmed_by == "hr_001"
    assert application.role == "后端开发"


def test_department_is_carried_by_prepared_intake_and_persisted(intake, resume_bytes):
    prepared = intake.prepare_draft(
        "resume.txt", resume_bytes, "", "后端开发", department=" 研发中心 "
    )

    assert prepared.department == "研发中心"
    _, application = intake.confirm(
        prepared.token, confirmed_by="hr", choice=ConfirmationChoice.NO_DUPLICATE
    )

    assert application.department == "研发中心"


def test_prepare_is_immutable_ui_payload_with_conflict_metadata(intake, resume_bytes):
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "两周到岗", "后端开发")
    assert prepared.document.filename == "resume.txt"
    assert prepared.document.mime_type == "text/plain"
    assert len(prepared.document.sha256) == 64
    assert prepared.usage.total_tokens == 18
    assert prepared.conflicts[0].field_name == "availability"
    with pytest.raises(Exception):
        prepared.role = "changed"
    with pytest.raises(Exception):
        prepared.draft.name = "changed"


def test_prepared_draft_is_deeply_immutable_and_service_state_is_unchanged(
    repo, clock, resume_bytes
):
    provider = Provider(
        CandidateDraft(
            name="张三",
            education=[{"school": "示例大学", "details": {"major": "CS"}}],
            skills=["Python"],
            field_sources={
                "name": FieldEvidence(source="resume_text", quote="姓名：张三", confidence=0.9)
            },
            ai_metadata={"model": {"labels": ["resume"]}},
        )
    )
    intake = IntakeService(repo, provider, clock=clock)
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "", "role")

    with pytest.raises((AttributeError, TypeError)):
        prepared.draft.skills.append("SQL")
    with pytest.raises(TypeError):
        prepared.draft.education[0]["school"] = "changed"
    with pytest.raises(TypeError):
        prepared.draft.education[0]["details"]["major"] = "changed"
    with pytest.raises(TypeError):
        prepared.draft.field_sources["name"] = FieldEvidence(
            source="boss_note", quote="changed", confidence=1
        )
    with pytest.raises(Exception):
        prepared.draft.field_sources["name"].quote = "changed"
    with pytest.raises(TypeError):
        prepared.draft.ai_metadata["model"]["labels"] += ("changed",)

    candidate, _ = intake.confirm(
        prepared.token, confirmed_by="hr", choice=ConfirmationChoice.NO_DUPLICATE
    )
    assert candidate.skills == ["Python"]
    assert candidate.education[0]["school"] == "示例大学"
    assert candidate.field_sources["name"]["quote"] == "姓名：张三"


@pytest.mark.parametrize("actor", ["", "  "])
def test_confirmation_requires_nonblank_actor(intake, resume_bytes, actor):
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "", "后端开发")
    with pytest.raises(IntakeValidationError, match="confirmed_by"):
        intake.confirm(prepared.token, confirmed_by=actor, choice=ConfirmationChoice.NO_DUPLICATE)


def test_hr_edits_are_validated_and_persisted(intake, repo, resume_bytes):
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "", "后端开发")
    edited = prepared.draft.model_copy(update={"name": "李四", "phone": "13900000000"})
    candidate, _ = intake.confirm(
        prepared.token,
        confirmed_by="hr_001",
        confirmed=edited,
        choice=ConfirmationChoice.NO_DUPLICATE,
    )
    stored = repo.list_candidates()[0]
    assert (candidate.name, stored.name, stored.phone) == ("李四", "李四", "13900000000")
    assert stored.ai_metadata["intake"]["document"]["filename"] == "resume.txt"
    assert stored.ai_metadata["usage"]["total_tokens"] == 18


def test_unknown_expired_consumed_and_idempotent_retry(repo, clock, resume_bytes):
    intake = IntakeService(repo, Provider(), clock=clock, ttl=timedelta(seconds=1))
    with pytest.raises(DraftNotFoundError):
        intake.confirm("unknown", confirmed_by="hr", choice=ConfirmationChoice.NO_DUPLICATE)
    expired = intake.prepare_draft("resume.txt", resume_bytes, "", "role")
    clock.now += timedelta(seconds=2)
    with pytest.raises(DraftExpiredError):
        intake.confirm(expired.token, confirmed_by="hr", choice=ConfirmationChoice.NO_DUPLICATE)

    clock.now -= timedelta(seconds=2)
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "", "role")
    first = intake.confirm(
        prepared.token,
        confirmed_by="hr",
        choice=ConfirmationChoice.NO_DUPLICATE,
        idempotency_key="submit-1",
    )
    assert (
        intake.confirm(
            prepared.token,
            confirmed_by="hr",
            choice=ConfirmationChoice.NO_DUPLICATE,
            idempotency_key="submit-1",
        )
        == first
    )
    with pytest.raises(DraftConsumedError):
        intake.confirm(
            prepared.token,
            confirmed_by="hr",
            choice=ConfirmationChoice.NO_DUPLICATE,
            idempotency_key="different",
        )


def test_duplicate_choice_is_explicit_and_never_silently_merges(repo, clock, resume_bytes):
    existing = repo.create_candidate(CandidateConfirmed(name="Existing", phone="13800000000"))
    intake = IntakeService(repo, Provider(), clock=clock)
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "secret note", "new role")
    assert [hint.candidate_id for hint in prepared.duplicate_hints] == [existing.id]
    with pytest.raises(IntakeValidationError, match="duplicate choice"):
        intake.confirm(prepared.token, confirmed_by="hr")
    with pytest.raises(IntakeValidationError, match="selected_candidate_id"):
        intake.confirm(
            prepared.token,
            confirmed_by="hr",
            choice=ConfirmationChoice.REUSE_DUPLICATE,
            selected_candidate_id=999,
        )
    candidate, application = intake.confirm(
        prepared.token,
        confirmed_by="hr",
        choice=ConfirmationChoice.REUSE_DUPLICATE,
        selected_candidate_id=existing.id,
    )
    assert candidate.id == existing.id
    assert application.candidate_id == existing.id
    assert len(repo.list_candidates()) == 1


def test_create_new_and_no_duplicate_choices_do_not_merge(repo, clock, resume_bytes):
    repo.create_candidate(CandidateConfirmed(name="Existing", email="zhang@example.com"))
    intake = IntakeService(repo, Provider(), clock=clock)
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "", "role")
    created, _ = intake.confirm(
        prepared.token, confirmed_by="hr", choice=ConfirmationChoice.CREATE_NEW
    )
    assert created.name == "张三"
    assert len(repo.list_candidates()) == 2


def test_same_role_duplicate_reuse_is_rejected(repo, clock, resume_bytes):
    existing = repo.create_candidate(CandidateConfirmed(name="Existing", phone="13800000000"))
    repo.create_application(existing.id, role="role")
    intake = IntakeService(repo, Provider(), clock=clock)
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "", "role")
    with pytest.raises(IntakeValidationError, match="already has an application"):
        intake.confirm(
            prepared.token,
            confirmed_by="hr",
            choice=ConfirmationChoice.REUSE_DUPLICATE,
            selected_candidate_id=existing.id,
        )


def test_audit_and_jobs_are_safe_and_pending(intake, repo, resume_bytes):
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "TOP SECRET NOTE", "role")
    candidate, application = intake.confirm(
        prepared.token,
        confirmed_by="hr",
        confirmed=prepared.draft.model_copy(update={"name": "Edited"}),
        choice=ConfirmationChoice.NO_DUPLICATE,
    )
    audits = repo.list_audit_events()
    jobs = repo.list_sync_jobs()
    serialized = json.dumps(
        [event.payload for event in audits] + [job.payload for job in jobs], ensure_ascii=False
    )
    assert resume_bytes.decode() not in serialized
    assert "TOP SECRET NOTE" not in serialized
    assert audits[0].actor == "hr"
    assert audits[0].payload["changed_fields"] == ["name"]
    assert {job.provider for job in jobs} == {"candidate_docs", "department_notification"}
    assert all(job.status.value == "pending" for job in jobs)
    assert str(candidate.id) in serialized and str(application.id) in serialized


def test_conflict_retains_both_values_and_sources_for_hr(intake, resume_bytes):
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "两周到岗", "role")
    conflict = prepared.conflicts[0]
    assert conflict.field_name == "availability"
    assert conflict.resume_value == "一个月到岗"
    assert conflict.resume_source == "resume_text"
    assert conflict.note_value == "两周到岗"
    assert conflict.note_source == "boss_note"


def test_pii_filename_is_absent_from_audit_and_sync_payloads(repo, clock, resume_bytes):
    intake = IntakeService(repo, Provider(), clock=clock)
    filename = "张三_13800000000_简历.txt"
    prepared = intake.prepare_draft(filename, resume_bytes, "", "role")
    assert prepared.document.filename == filename
    intake.confirm(prepared.token, confirmed_by="hr", choice=ConfirmationChoice.NO_DUPLICATE)
    serialized = json.dumps(
        [event.payload for event in repo.list_audit_events()]
        + [job.payload for job in repo.list_sync_jobs()],
        ensure_ascii=False,
    )
    for pii in (filename, "张三", "13800000000", "简历"):
        assert pii not in serialized


def test_confirmation_rolls_back_candidate_application_audit_and_jobs(
    intake, repo, resume_bytes, monkeypatch
):
    prepared = intake.prepare_draft("resume.txt", resume_bytes, "", "role")
    original_transaction = repo.transaction

    class FailingTransaction:
        def __init__(self):
            self.inner = original_transaction()
            self.jobs = 0

        def __enter__(self):
            self.inner.__enter__()
            return self

        def __exit__(self, *args):
            return self.inner.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.inner, name)

        def upsert_sync_job(self, *args, **kwargs):
            self.jobs += 1
            if self.jobs == 2:
                raise RuntimeError("queue unavailable")
            return self.inner.upsert_sync_job(*args, **kwargs)

    monkeypatch.setattr(repo, "transaction", FailingTransaction)
    with pytest.raises(RuntimeError, match="queue unavailable"):
        intake.confirm(prepared.token, confirmed_by="hr", choice=ConfirmationChoice.NO_DUPLICATE)
    assert repo.list_candidates() == []
    assert repo.list_applications() == []
    assert repo.list_audit_events() == []
    assert repo.list_sync_jobs() == []


@pytest.mark.parametrize(("filename", "content"), [("resume.exe", b"no"), ("resume.txt", b"\xff")])
def test_bad_documents_map_to_clear_service_error(intake, filename, content):
    with pytest.raises(IntakeValidationError, match="document"):
        intake.prepare_draft(filename, content, "", "role")


def test_role_must_not_be_blank(intake, resume_bytes):
    with pytest.raises(IntakeValidationError, match="role"):
        intake.prepare_draft("resume.txt", resume_bytes, "", " ")
