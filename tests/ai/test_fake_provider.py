from pathlib import Path

import pytest

from src.ai.fake_provider import FakeAIProvider
from src.domain.models import FeedbackDecision


def test_extract_candidate_uses_resume_and_boss_note_evidence() -> None:
    result = FakeAIProvider().extract_candidate(
        resume_text="姓名：林晓\n院校：示例大学",
        hr_notes="期望薪资 20k；两周到岗",
        images=[],
    )

    draft = result.draft
    assert draft.name == "林晓"
    assert draft.expected_salary == "20k"
    assert draft.availability == "两周到岗"
    assert draft.field_sources["expected_salary"].source == "boss_note"
    assert result.usage.total_tokens == 0


def test_extract_candidate_reads_common_resume_contact_and_profile_fields() -> None:
    result = FakeAIProvider().extract_candidate(
        resume_text=(
            "姓名：王明\n"
            "电话：138 0000 0000\n"
            "邮箱：wangming@example.com\n"
            "当前城市：上海\n"
            "年龄：24\n"
            "性别：男\n"
            "期望薪资：18k\n"
            "到岗时间：随时到岗\n"
            "毕业院校：复旦大学，计算机科学本科\n"
            "实习经历：腾讯 数据分析实习生，负责 SQL 报表和 Python 自动化。\n"
            "技能：Python、SQL、Tableau、Excel\n"
        ),
        hr_notes="BOSS沟通：候选人说期望薪资 20k，最快两周到岗",
        images=[],
    )

    draft = result.draft
    assert draft.name == "王明"
    assert draft.phone == "138 0000 0000"
    assert draft.email == "wangming@example.com"
    assert draft.current_city == "上海"
    assert draft.expected_salary == "20k"
    assert draft.availability == "两周到岗"
    assert draft.education[0]["school"] == "复旦大学"
    assert draft.internship_experience[0]["company"] == "腾讯"
    assert "Tableau" in draft.skills
    assert draft.ai_metadata["profile"]["age"] == "24"
    assert draft.ai_metadata["profile"]["gender"] == "男"
    assert draft.field_sources["phone"].source == "resume_text"
    assert draft.field_sources["expected_salary"].source == "boss_note"


def test_extract_anonymized_sample_is_deterministic() -> None:
    resume = Path("samples/anonymous-resume.txt").read_text(encoding="utf-8")
    provider = FakeAIProvider()

    first = provider.extract_candidate(resume, "", ())
    second = provider.extract_candidate(resume, "", [])

    assert first == second
    assert first.draft.name == "林晓"
    assert first.draft.education[0]["school"] == "示例大学"
    assert first.draft.skills[:2] == ["Python", "SQL"]
    assert first.draft.phone is None
    assert first.draft.field_sources["name"].quote == "姓名：林晓（化名）"


def test_feedback_only_classifies_explicit_seeded_phrases() -> None:
    provider = FakeAIProvider()

    passed = provider.classify_feedback("技术面通过，建议进入下一轮")
    unclear = provider.classify_feedback("候选人沟通顺畅")

    assert passed.classification.decision == FeedbackDecision.PASS
    assert passed.classification.evidence_quote == "技术面通过"
    assert unclear.classification.decision == FeedbackDecision.UNCLEAR
    assert unclear.classification.requires_human_confirmation is True


@pytest.mark.parametrize("text", ["不建议进入下一轮", "技术面不通过"])
def test_feedback_negation_is_never_misclassified_as_pass(text: str) -> None:
    classification = FakeAIProvider().classify_feedback(text).classification

    assert classification.decision == FeedbackDecision.FAIL
    assert classification.requires_human_confirmation is True


def test_conflicting_feedback_is_unclear() -> None:
    classification = (
        FakeAIProvider()
        .classify_feedback("技术面通过，但综合意见是不建议进入下一轮")
        .classification
    )

    assert classification.decision == FeedbackDecision.UNCLEAR
    assert classification.requires_human_confirmation is True
