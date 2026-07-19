# Recruitment AI Automation Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a directly runnable AI recruitment Demo that parses resumes and BOSS chat notes, requires HR confirmation, tracks role-specific multi-round interviews, understands free-text feedback, syncs through replaceable Tencent Docs/WeCom adapters, and shows a live dashboard.

**Architecture:** Use one Python Streamlit application to minimize deployment and maintenance cost. Domain services and adapter interfaces stay independent of the UI; SQLite is the Demo source of truth, while local/mock adapters make the full workflow runnable without enterprise credentials and real adapters can be enabled by environment variables. OpenAI structured outputs provide resume extraction and feedback classification, with a deterministic fake provider for tests and offline demonstrations.

**Tech Stack:** Python 3.12, Streamlit, SQLModel/SQLite, OpenAI Python SDK, Pydantic v2, pypdf, python-docx, Pillow, pytest, Ruff, Docker, GitHub Actions.

---

## Scope and delivery boundary

This plan produces a working MVP Demo, not a production ATS. The Demo includes real model calls when `OPENAI_API_KEY` is configured and a seeded offline mode when it is not. Tencent Docs and WeCom use demonstrable mock adapters by default; production API adapters are interface-compatible but must not be claimed as working until enterprise credentials and API permissions are supplied and integration-tested.

Expected deliverables after execution:

- Source code in this workspace, with a setup guide and sample anonymized resumes.
- One-command local launch with `docker compose up --build` or `streamlit run src/app.py`.
- Automated tests and a GitHub Actions verification workflow.
- A deployable Docker image definition.
- After the user authorizes publication and supplies a Git host/deployment target: a repository URL and a live preview URL.

## File map

```text
src/
  app.py                       # Streamlit navigation and page composition only
  config.py                    # Environment-backed settings
  domain/models.py             # Pydantic domain contracts and enums
  db/models.py                 # SQLModel persistence tables
  db/repository.py             # Candidate/application/interview persistence API
  ai/protocol.py               # AI provider interface
  ai/openai_provider.py        # Real structured-output model calls
  ai/fake_provider.py          # Deterministic offline/test provider
  documents/extract_text.py    # PDF, DOCX, TXT and image input normalization
  services/intake.py           # Upload, AI draft, duplicate hints, HR confirmation
  services/workflow.py         # Role templates, stage transitions and interviews
  services/feedback.py         # Standard and AI-classified feedback handling
  services/sync.py             # Idempotent sync orchestration and retry state
  adapters/wecom.py            # Mock and webhook notification adapters
  adapters/tencent_docs.py     # Mock and future real sync adapter boundary
  ui/intake_page.py            # Upload and HR confirmation UI
  ui/pipeline_page.py          # Candidate and interview workflow UI
  ui/dashboard_page.py         # KPI and exception dashboard
tests/                         # Unit, service and smoke tests mirroring src boundaries
samples/                       # Anonymized Demo inputs
.streamlit/config.toml         # Safe upload/theme defaults
.env.example                   # Documented configuration contract
pyproject.toml                 # Dependencies and tool configuration
Dockerfile                     # Reproducible Demo image
compose.yaml                   # Local persistent volume and port mapping
.github/workflows/ci.yml       # Lint and test checks
README.md                      # Runbook, Demo script and deployment instructions
```

### Task 1: Bootstrap the runnable application and quality gates

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.streamlit/config.toml`
- Create: `src/__init__.py`
- Create: `src/app.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/test_smoke.py
def test_app_module_imports() -> None:
    from src.app import APP_TITLE

    assert APP_TITLE == "招聘数据 AI 自动化 Demo"
```

- [ ] **Step 2: Run the test and verify the expected failure**

Run: `pytest tests/test_smoke.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.app'`.

- [ ] **Step 3: Add project configuration and the minimal app**

```toml
# pyproject.toml
[project]
name = "recruitment-ai-demo"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "streamlit>=1.40,<2",
  "sqlmodel>=0.0.22,<0.1",
  "openai>=1.60,<2",
  "pydantic-settings>=2.7,<3",
  "pypdf>=5,<6",
  "python-docx>=1.1,<2",
  "pillow>=11,<12",
  "httpx>=0.28,<1",
]

[project.optional-dependencies]
dev = ["pytest>=8,<9", "pytest-cov>=6,<7", "ruff>=0.9,<1"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
```

```python
# src/app.py
import streamlit as st

APP_TITLE = "招聘数据 AI 自动化 Demo"


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.info("Demo 初始化完成。后续任务将加入简历解析、流程和看板。")


if __name__ == "__main__":
    main()
```

Set `.streamlit/config.toml` to `maxUploadSize = 20`, and document `OPENAI_API_KEY`, `OPENAI_MODEL`, `DATABASE_URL`, `AI_MODE`, `WECOM_WEBHOOK_URL`, and `TENCENT_DOCS_MODE` in `.env.example` without real secrets.

- [ ] **Step 4: Run lint and tests**

Run: `ruff check src tests && pytest -q`
Expected: PASS, `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example .streamlit src tests
git commit -m "chore: bootstrap recruitment AI demo"
```

### Task 2: Define stable domain contracts and persistence schema

**Files:**
- Create: `src/domain/models.py`
- Create: `src/db/models.py`
- Create: `src/db/repository.py`
- Create: `tests/db/test_repository.py`

- [ ] **Step 1: Write repository tests for one candidate, multiple applications, and appended interview rounds**

```python
# tests/db/test_repository.py
from src.db.repository import Repository
from src.domain.models import CandidateConfirmed, InterviewInput


def test_candidate_can_have_multiple_applications_and_rounds(tmp_path) -> None:
    repo = Repository(f"sqlite:///{tmp_path}/test.db")
    candidate = repo.create_candidate(CandidateConfirmed(name="林晓", phone="13800000000"))
    app_a = repo.create_application(candidate.id, role="后端开发", department="研发")
    app_b = repo.create_application(candidate.id, role="数据分析", department="产品")
    repo.append_interview(app_a.id, InterviewInput(round_name="技术初试", interviewer="王经理"))
    repo.append_interview(app_a.id, InterviewInput(round_name="技术复试", interviewer="陈总"))

    assert app_a.id != app_b.id
    assert [item.round_name for item in repo.list_interviews(app_a.id)] == ["技术初试", "技术复试"]
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `pytest tests/db/test_repository.py -q`
Expected: FAIL because repository and domain modules do not exist.

- [ ] **Step 3: Implement enums, contracts, tables, and repository methods**

Define these exact domain types in `src/domain/models.py`: `CandidateDraft`, `CandidateConfirmed`, `FieldEvidence`, `ApplicationStatus`, `FeedbackDecision`, `FeedbackClassification`, `InterviewInput`, `InterviewOutcome`, and `RoleTemplate`. `CandidateDraft` must hold `field_sources: dict[str, FieldEvidence]`; `FieldEvidence` must contain `source`, `quote`, and `confidence`. `FeedbackClassification` must contain `decision`, `reason`, `evidence_quote`, `confidence`, and `requires_human_confirmation`.

Define SQLModel tables in `src/db/models.py`: `CandidateRow`, `ApplicationRow`, `InterviewRoundRow`, `RoleTemplateRow`, `AuditEventRow`, and `SyncJobRow`. Every mutable table must have `created_at` and `updated_at`; interview and audit rows are append-only.

Implement `Repository` methods used in the test plus `find_duplicate_candidates`, `save_role_template`, `instantiate_template`, `update_application_status`, `append_audit_event`, `upsert_sync_job`, and dashboard aggregate queries. All write methods must commit atomically and return refreshed rows.

- [ ] **Step 4: Run schema and repository tests**

Run: `pytest tests/db/test_repository.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/domain src/db tests/db
git commit -m "feat: add recruitment domain and persistence model"
```

### Task 3: Normalize resume documents into model-ready content

**Files:**
- Create: `src/documents/extract_text.py`
- Create: `tests/documents/test_extract_text.py`
- Create: `samples/anonymous-resume.txt`

- [ ] **Step 1: Write format and safety tests**

```python
# tests/documents/test_extract_text.py
import pytest
from src.documents.extract_text import UnsupportedDocument, extract_document


def test_extracts_utf8_text() -> None:
    result = extract_document("resume.txt", b"姓名：林晓\n院校：示例大学")
    assert "林晓" in result.text
    assert result.mime_type == "text/plain"


def test_rejects_executable_content() -> None:
    with pytest.raises(UnsupportedDocument):
        extract_document("resume.exe", b"MZ")
```

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/documents/test_extract_text.py -q`
Expected: FAIL because `extract_document` is missing.

- [ ] **Step 3: Implement extraction**

Create `ExtractedDocument(filename, mime_type, text, image_bytes)` and support `.pdf`, `.docx`, `.txt`, `.png`, `.jpg`, and `.jpeg`. Extract text locally from text PDFs/DOCX/TXT; return bounded image bytes for scanned pages/images so the AI provider can use vision. Reject files over 20 MB, password-protected PDFs, executable extensions, empty files, and extracted text over 100,000 characters with explicit Chinese error messages.

- [ ] **Step 4: Run document tests**

Run: `pytest tests/documents/test_extract_text.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/documents tests/documents samples
git commit -m "feat: normalize resume documents safely"
```

### Task 4: Add actual AI extraction with structured output and an offline provider

**Files:**
- Create: `src/ai/protocol.py`
- Create: `src/ai/openai_provider.py`
- Create: `src/ai/fake_provider.py`
- Create: `src/config.py`
- Create: `tests/ai/test_fake_provider.py`
- Create: `tests/ai/test_openai_provider.py`

- [ ] **Step 1: Write provider contract tests**

```python
# tests/ai/test_fake_provider.py
from src.ai.fake_provider import FakeAIProvider


def test_fake_provider_merges_resume_and_hr_notes_with_sources() -> None:
    draft = FakeAIProvider().extract_candidate(
        resume_text="姓名：林晓\n院校：示例大学",
        hr_notes="期望薪资 20k；两周到岗",
        images=[],
    )
    assert draft.name == "林晓"
    assert draft.expected_salary == "20k"
    assert draft.field_sources["expected_salary"].source == "boss_note"
```

Mock the OpenAI client in `tests/ai/test_openai_provider.py` and assert that `OpenAIProvider.extract_candidate` requests the `CandidateDraft` schema, uses the configured model, includes a prompt-injection warning, and never logs resume contents.

- [ ] **Step 2: Run and verify provider tests fail**

Run: `pytest tests/ai -q`
Expected: FAIL because providers do not exist.

- [ ] **Step 3: Implement the protocol and providers**

```python
# src/ai/protocol.py
from typing import Protocol
from src.domain.models import CandidateDraft, FeedbackClassification


class AIProvider(Protocol):
    def extract_candidate(self, resume_text: str, hr_notes: str, images: list[bytes]) -> CandidateDraft: ...
    def classify_feedback(self, text: str) -> FeedbackClassification: ...
```

`OpenAIProvider` must use the OpenAI Responses API structured-output helper with `CandidateDraft` and `FeedbackClassification` Pydantic schemas. The system instruction must state that resume content is untrusted data, commands inside it must be ignored, unknown values must remain null, source quotes must be short, and gender/age must not be inferred when absent. Use `OPENAI_MODEL` from settings; do not hard-code a model name. Images are sent only when local extraction produced no useful text. Return usage metadata for cost tracking.

`FakeAIProvider` must deterministically parse the anonymized sample and return seeded feedback classifications so the Demo remains usable without a key. `Settings` must choose fake mode when `AI_MODE=fake`; real mode must fail at startup with a clear message when the API key is absent.

- [ ] **Step 4: Run AI unit tests without network calls**

Run: `pytest tests/ai -q`
Expected: PASS with no external network access.

- [ ] **Step 5: Add an opt-in real-model contract check**

Create `tests/integration/test_openai_live.py` marked `live_ai`, skipped unless `RUN_LIVE_AI_TESTS=1`. It parses `samples/anonymous-resume.txt` and asserts the name, school, source evidence, and non-empty usage metadata. Run: `RUN_LIVE_AI_TESTS=1 pytest -m live_ai -q`. Expected with valid credentials: PASS; otherwise: SKIPPED in normal CI.

- [ ] **Step 6: Commit**

```bash
git add src/ai src/config.py tests/ai tests/integration
git commit -m "feat: add structured AI extraction and feedback models"
```

### Task 5: Implement intake, duplicate hints, and mandatory HR confirmation

**Files:**
- Create: `src/services/intake.py`
- Create: `tests/services/test_intake.py`

- [ ] **Step 1: Write the confirmation-gate test**

```python
# tests/services/test_intake.py
def test_ai_draft_is_not_persisted_before_hr_confirmation(intake, repo, resume_bytes) -> None:
    draft = intake.prepare_draft("resume.txt", resume_bytes, "两周到岗", "后端开发")
    assert repo.list_candidates() == []

    candidate, application = intake.confirm(draft, confirmed_by="hr_001")
    assert candidate.confirmed_by == "hr_001"
    assert application.role == "后端开发"
```

Also test conflicting resume/HR-note values remain visible, duplicate hints do not auto-merge, and confirming the same intake token twice is idempotent.

- [ ] **Step 2: Verify focused tests fail**

Run: `pytest tests/services/test_intake.py -q`
Expected: FAIL because `IntakeService` is missing.

- [ ] **Step 3: Implement `IntakeService`**

`prepare_draft` must normalize the document, call the AI provider, add immutable source evidence, compute duplicate hints, and return an expiring draft token without creating a candidate. `confirm` must validate editable fields, require `confirmed_by`, store original file metadata, atomically create/reuse the candidate and application, append an audit event, and enqueue sync/notification jobs. Never auto-merge duplicate candidates.

- [ ] **Step 4: Run intake tests**

Run: `pytest tests/services/test_intake.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/intake.py tests/services/test_intake.py
git commit -m "feat: require HR confirmation for AI candidate drafts"
```

### Task 6: Implement role-specific workflow templates and interview history

**Files:**
- Create: `src/services/workflow.py`
- Create: `tests/services/test_workflow.py`

- [ ] **Step 1: Write workflow tests**

```python
# tests/services/test_workflow.py
def test_role_template_becomes_an_independent_application_instance(workflow, repo, application) -> None:
    workflow.save_template("后端开发", ["技术初试", "技术复试", "HR 面"])
    workflow.start(application.id)
    workflow.save_template("后端开发", ["技术初试", "HR 面"])

    assert workflow.stage_names(application.id) == ["技术初试", "技术复试", "HR 面"]


def test_interview_feedback_appends_and_advances(workflow, application) -> None:
    workflow.submit_interview(application.id, "王经理", "通过", "基础扎实")
    assert workflow.current_stage(application.id) == "技术复试"
    assert len(workflow.history(application.id)) == 1
```

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/services/test_workflow.py -q`
Expected: FAIL because workflow service is missing.

- [ ] **Step 3: Implement workflow state transitions**

Allow only documented transitions: `awaiting_hr_confirmation → department_screening → interviewing → offered/hired/rejected/withdrawn/cancelled`. Template stages are copied when interviewing starts. Allow HR to add or skip a stage only with a reason and audit event. Interview submissions append rows and never overwrite prior rounds. Repeated submissions with the same idempotency key return the original result.

- [ ] **Step 4: Run workflow tests**

Run: `pytest tests/services/test_workflow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/services/workflow.py tests/services/test_workflow.py
git commit -m "feat: add role templates and append-only interviews"
```

### Task 7: Add standardized and AI-assisted feedback intake

**Files:**
- Create: `src/services/feedback.py`
- Create: `tests/services/test_feedback.py`

- [ ] **Step 1: Write deterministic and low-confidence tests**

```python
# tests/services/test_feedback.py
def test_standard_decision_does_not_call_ai(feedback_service, spy_ai) -> None:
    result = feedback_service.interpret("通过", reason="经验匹配")
    assert result.decision.value == "pass"
    assert spy_ai.calls == 0


def test_low_confidence_free_text_requires_confirmation(feedback_service) -> None:
    result = feedback_service.interpret("感觉还可以，再看看")
    assert result.requires_human_confirmation is True
```

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/services/test_feedback.py -q`
Expected: FAIL because feedback service is missing.

- [ ] **Step 3: Implement feedback interpretation**

Map exact standard actions (`通过`, `不通过`, `待定`) without AI. Send all other text to `AIProvider.classify_feedback`. Require human confirmation when confidence is below `0.85`, the decision is ambiguous, or the model supplies no short evidence quote. Persist original text and confirmed structured result separately.

- [ ] **Step 4: Run feedback tests and commit**

Run: `pytest tests/services/test_feedback.py -q`
Expected: PASS.

```bash
git add src/services/feedback.py tests/services/test_feedback.py
git commit -m "feat: structure hiring feedback with AI fallback"
```

### Task 8: Add WeCom/Tencent Docs adapter boundaries and reliable sync

**Files:**
- Create: `src/adapters/wecom.py`
- Create: `src/adapters/tencent_docs.py`
- Create: `src/services/sync.py`
- Create: `tests/services/test_sync.py`

- [ ] **Step 1: Write retry and attachment-access tests**

```python
# tests/services/test_sync.py
def test_failed_docs_sync_stays_queued(sync_service, failing_docs, application) -> None:
    sync_service.enqueue_application(application.id)
    sync_service.run_once()
    job = sync_service.get_job(application.id)
    assert job.status == "retrying"
    assert job.attempts == 1


def test_docs_row_contains_controlled_resume_reference(sync_service, recording_docs, application) -> None:
    sync_service.enqueue_application(application.id)
    sync_service.run_once()
    assert recording_docs.rows[0]["resume_access"] == "authenticated_link"
```

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/services/test_sync.py -q`
Expected: FAIL because adapters and sync service are missing.

- [ ] **Step 3: Implement adapters and sync semantics**

Create protocols `WeComNotifier.send_candidate_card(...)` and `TencentDocsGateway.upsert_candidate_row(...)`. Implement `MockWeComNotifier` and `MockTencentDocsGateway` that record payloads for the Demo. Implement `WebhookWeComNotifier` for outbound group notifications only. Keep the production Tencent Docs implementation behind `TENCENT_DOCS_MODE=real` and raise `IntegrationNotConfigured` unless credentials and document identifiers exist; do not fake a successful external write.

`SyncService` must use idempotency keys, exponential retry scheduling, persisted attempts, and `pending/succeeded/retrying/dead_letter` states. Database changes remain committed when external sync fails.

- [ ] **Step 4: Run sync tests and commit**

Run: `pytest tests/services/test_sync.py -q`
Expected: PASS.

```bash
git add src/adapters src/services/sync.py tests/services/test_sync.py
git commit -m "feat: add reliable recruitment integration adapters"
```

### Task 9: Build the interactive Streamlit Demo

**Files:**
- Create: `src/ui/intake_page.py`
- Create: `src/ui/pipeline_page.py`
- Create: `src/ui/dashboard_page.py`
- Modify: `src/app.py`
- Create: `tests/ui/test_view_models.py`

- [ ] **Step 1: Write tests for UI view models**

```python
# tests/ui/test_view_models.py
def test_dashboard_view_has_operational_metrics(dashboard_vm) -> None:
    view = dashboard_vm.build()
    assert set(view.metrics) >= {"new", "awaiting_confirmation", "screening", "interviewing", "hired"}
    assert "sync_failures" in view.exceptions
```

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/ui/test_view_models.py -q`
Expected: FAIL because UI view models are missing.

- [ ] **Step 3: Implement three usable pages**

`intake_page.py` must provide upload, role selection, BOSS-note paste, AI processing status, side-by-side original evidence and editable fields, duplicate hints, and explicit “确认建档”. `pipeline_page.py` must provide candidate filters, authenticated Demo attachment links, standardized screening actions, role-template stages, interview forms, history, and terminal states. `dashboard_page.py` must show counts, conversion rates, stage duration, channel results, AI usage/cost estimate, and actionable exception rows.

`src/app.py` must create settings, repository, AI provider, services, and adapters once with `st.cache_resource`; sidebar navigation selects the three pages. Display a visible “离线演示模式” banner when fake AI or mock integrations are active, so mock behavior cannot be mistaken for a live enterprise integration.

- [ ] **Step 4: Run unit tests and a local UI smoke test**

Run: `pytest -q && streamlit run src/app.py --server.headless true`
Expected: tests PASS; browser opens the Demo with three pages and no traceback.

- [ ] **Step 5: Execute the Demo acceptance script manually**

Upload `samples/anonymous-resume.txt`, paste `期望薪资 20k，两周到岗`, edit one field, confirm, screen as passed, submit two interview rounds, and verify the candidate row, history, dashboard, mock notification, and mock Tencent Docs payload all update.

- [ ] **Step 6: Commit**

```bash
git add src/app.py src/ui tests/ui
git commit -m "feat: deliver interactive recruitment workflow demo"
```

### Task 10: Package, secure, document, and verify the deliverable

**Files:**
- Create: `Dockerfile`
- Create: `compose.yaml`
- Create: `.dockerignore`
- Create: `.github/workflows/ci.yml`
- Create: `README.md`
- Create: `tests/test_security_guards.py`

- [ ] **Step 1: Write security regression tests**

```python
# tests/test_security_guards.py
from pathlib import Path


def test_repository_contains_no_real_secrets() -> None:
    forbidden = ("sk-", "corpsecret", "BEGIN PRIVATE KEY")
    text = "\n".join(
        path.read_text(errors="ignore")
        for path in Path(".").rglob("*")
        if path.is_file() and ".git" not in path.parts
    )
    assert not any(token in text for token in forbidden)
```

- [ ] **Step 2: Add reproducible runtime files**

Use a non-root Python 3.12 slim image, install the package, expose port 8501, persist `/app/data`, and add a health check against `/_stcore/health`. `compose.yaml` must mount a named SQLite/attachment volume and read secrets only from environment variables.

- [ ] **Step 3: Add CI**

`.github/workflows/ci.yml` must run on pushes and pull requests with Python 3.12, install `.[dev]`, run `ruff check src tests`, then `pytest --cov=src --cov-report=term-missing --cov-fail-under=80`. Live AI tests remain opt-in and never run with untrusted pull-request secrets.

- [ ] **Step 4: Write the operator and Demo guide**

`README.md` must include architecture, capability matrix (real vs mock), local Python launch, Docker launch, OpenAI configuration, data reset, sample Demo walkthrough, privacy limitations, Tencent/WeCom credential prerequisites, troubleshooting, and production-hardening gaps. State explicitly that a public preview must use anonymized sample data only.

- [ ] **Step 5: Run final verification**

Run: `ruff check src tests && pytest --cov=src --cov-report=term-missing --cov-fail-under=80 && docker compose config && docker build -t recruitment-ai-demo:local .`
Expected: lint PASS, tests PASS with at least 80% coverage, Compose config valid, Docker image builds successfully.

- [ ] **Step 6: Run the container smoke test**

Run: `docker compose up --build`, then open `http://localhost:8501/_stcore/health`.
Expected: HTTP 200 and the application loads at `http://localhost:8501`.

- [ ] **Step 7: Commit**

```bash
git add Dockerfile compose.yaml .dockerignore .github README.md tests/test_security_guards.py
git commit -m "docs: package and verify recruitment AI demo"
```

### Task 11: Publish code and an online preview after explicit authorization

**Files:**
- Modify: `README.md`
- Modify: `.env.example`

- [ ] **Step 1: Confirm external publication scope**

Before creating a repository or deployment, obtain the user’s explicit choice of GitHub owner/repository visibility and hosting target. Confirm that only anonymized sample data will be published. This step is intentionally blocking because publication changes external state.

- [ ] **Step 2: Initialize version control if still absent**

Run: `git init -b main && git add . && git commit -m "feat: deliver recruitment AI automation demo"`
Expected: a clean `main` branch with no secrets; skip this command if execution began inside an existing repository.

- [ ] **Step 3: Publish the repository**

Use the approved GitHub workflow to create the repository and push `main`. Expected: a user-accessible repository URL. Do not invent or report a URL until the remote confirms it.

- [ ] **Step 4: Deploy the preview**

Deploy the Docker image or Streamlit app to the user-approved hosting target in fake-AI/mock-integration mode, with anonymized samples only. Configure health checks and no persistent personal data. Expected: a reachable HTTPS preview URL.

- [ ] **Step 5: Verify external links and document them**

Open both the repository and preview URLs, complete the anonymized intake workflow, and add the verified URLs plus deployment limitations to `README.md`. Expected: code link loads, preview health check succeeds, and the Demo workflow completes.

- [ ] **Step 6: Commit and push deployment documentation**

```bash
git add README.md .env.example
git commit -m "docs: add verified demo and source links"
git push
```

## Plan self-review result

- Spec coverage: upload, AI prefill, HR confirmation, source evidence, duplicate hints, candidate/application separation, role templates, append-only interviews, standardized/free-text feedback, full-resume reference, Tencent/WeCom boundaries, retries, dashboard, auditability, security, cost visibility, tests, packaging, source publication, and preview deployment each map to a task above.
- Scope: production recruiting-platform ingestion and unverified enterprise API integration remain explicitly outside this Demo plan.
- Type consistency: `CandidateDraft`, `CandidateConfirmed`, `FeedbackClassification`, `AIProvider`, repository identifiers, and application/interview concepts are introduced before their service and UI use.
- Placeholder scan: passed; external publication is a deliberate authorization gate with exact verification criteria.
