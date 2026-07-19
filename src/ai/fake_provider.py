import re

from src.ai.protocol import (
    AIUsage,
    CandidateExtractionResult,
    FeedbackClassificationResult,
)
from src.domain.models import (
    CandidateDraft,
    FeedbackClassification,
    FeedbackDecision,
    FieldEvidence,
)


def _evidence(source: str, quote: str, confidence: float = 0.95) -> FieldEvidence:
    return FieldEvidence(source=source, quote=quote.strip()[:120], confidence=confidence)


def _first_match(text: str, pattern: str) -> re.Match[str] | None:
    return re.search(pattern, text, re.MULTILINE | re.IGNORECASE)


def _line_after_label(text: str, labels: tuple[str, ...]) -> re.Match[str] | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    return _first_match(text, rf"^(?:{label_pattern})[：:\s]*([^\n；;，,]+)")


class FakeAIProvider:
    """Small deterministic parser for demos and offline tests."""

    def extract_candidate(
        self, resume_text: str, hr_notes: str, images: list[bytes] | tuple[bytes, ...]
    ) -> CandidateExtractionResult:
        if not isinstance(images, (list, tuple)):
            raise TypeError("images must be a list or tuple")
        sources: dict[str, FieldEvidence] = {}
        values: dict[str, object] = {"hr_notes": hr_notes or None}

        name_match = re.search(r"^姓名[：:]\s*([^\n（(]+)", resume_text, re.MULTILINE)
        if name_match:
            values["name"] = name_match.group(1).strip()
            quote = name_match.group(0)
            suffix = resume_text[name_match.end() :].splitlines()[0]
            if suffix.startswith(("（", "(")):
                quote += suffix
            sources["name"] = _evidence("resume_text", quote)

        phone_match = _first_match(
            resume_text,
            r"(?:电话|手机|联系电话)[：:\s]*((?:\+?86[-\s]?)?1[3-9]\d[-\s]?\d{4}[-\s]?\d{4})",
        )
        if phone_match:
            values["phone"] = phone_match.group(1).strip()
            sources["phone"] = _evidence("resume_text", phone_match.group(0), 0.96)

        email_match = _first_match(
            resume_text,
            r"(?:邮箱|Email|E-mail)[：:\s]*([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
        )
        if email_match:
            values["email"] = email_match.group(1).strip()
            sources["email"] = _evidence("resume_text", email_match.group(0), 0.97)

        city_match = _line_after_label(resume_text, ("当前城市", "所在城市", "城市", "现居地"))
        if city_match:
            values["current_city"] = city_match.group(1).strip()
            sources["current_city"] = _evidence("resume_text", city_match.group(0), 0.9)

        school_match = _first_match(
            resume_text,
            r"(?:毕业院校|院校|学校)[：:\s]*([^\n，,；;]+)|^([^：:\n，,；;]*(?:大学|学院))[，,]",
        )
        if school_match:
            school = (school_match.group(1) or school_match.group(2)).strip()
            values["education"] = [{"school": school}]
            sources["education"] = _evidence("resume_text", school_match.group(0), 0.92)

        skill_keywords = (
            "Python",
            "SQL",
            "Excel",
            "Tableau",
            "Power BI",
            "数据可视化",
            "基础统计分析",
            "机器学习",
            "Java",
            "Go",
            "产品设计",
        )
        skills = [skill for skill in skill_keywords if re.search(re.escape(skill), resume_text, re.I)]
        if skills:
            values["skills"] = skills
            sources["skills"] = _evidence("resume_text", "、".join(skills), 0.93)

        internship_match = _first_match(
            resume_text,
            r"实习经历[：:\s]*([^\s，,；;]+)\s+([^。\n]+)",
        )
        if internship_match:
            values["internship_experience"] = [
                {"company": internship_match.group(1), "summary": internship_match.group(2).strip()}
            ]
            sources["internship_experience"] = _evidence(
                "resume_text", internship_match.group(0), 0.85
            )

        profile: dict[str, str] = {}
        age_match = _line_after_label(resume_text, ("年龄",))
        if age_match:
            profile["age"] = age_match.group(1).strip()
            sources["age"] = _evidence("resume_text", age_match.group(0), 0.9)
        gender_match = _line_after_label(resume_text, ("性别",))
        if gender_match:
            profile["gender"] = gender_match.group(1).strip()
            sources["gender"] = _evidence("resume_text", gender_match.group(0), 0.9)
        if profile:
            values["ai_metadata"] = {"profile": profile}

        salary_match = re.search(
            r"期望薪资[：:\s]*([0-9]+(?:\.[0-9]+)?\s*[kKwW万]?)", resume_text
        )
        if salary_match:
            values["expected_salary"] = salary_match.group(1).replace(" ", "")
            sources["expected_salary"] = _evidence("resume_text", salary_match.group(0), 0.88)

        note_salary_match = re.search(
            r"期望薪资[：:\s]*([0-9]+(?:\.[0-9]+)?\s*[kKwW万]?)", hr_notes
        )
        if note_salary_match:
            values["expected_salary"] = note_salary_match.group(1).replace(" ", "")
            sources["expected_salary"] = _evidence("boss_note", note_salary_match.group(0))

        resume_availability_match = re.search(
            r"(?:到岗时间[：:\s]*)?((?:一|二|两|三|四|五|六|七|八|九|十|\d+)周到岗|随时到岗)",
            resume_text,
        )
        if resume_availability_match:
            values["availability"] = resume_availability_match.group(1)
            sources["availability"] = _evidence(
                "resume_text", resume_availability_match.group(0), 0.88
            )

        availability_match = re.search(
            r"((?:一|二|两|三|四|五|六|七|八|九|十|\d+)周到岗|随时到岗)", hr_notes
        )
        if availability_match:
            values["availability"] = availability_match.group(1)
            sources["availability"] = _evidence("boss_note", availability_match.group(1))

        draft = CandidateDraft(**values, field_sources=sources)
        return CandidateExtractionResult(draft=draft, usage=AIUsage())

    def classify_feedback(self, text: str) -> FeedbackClassificationResult:
        negative_phrases = (
            "不建议进入下一轮",
            "技术面不通过",
            "面试不通过",
            "不通过",
            "不予录用",
            "淘汰",
        )
        positive_phrases = ("技术面通过", "面试通过", "建议进入下一轮")
        hold_phrases = ("暂缓", "待定", "保留")
        matched_groups = [
            (FeedbackDecision.FAIL, [phrase for phrase in negative_phrases if phrase in text]),
            (FeedbackDecision.PASS, [phrase for phrase in positive_phrases if phrase in text]),
            (FeedbackDecision.HOLD, [phrase for phrase in hold_phrases if phrase in text]),
        ]
        explicit = [(decision, phrases) for decision, phrases in matched_groups if phrases]
        independent_positive = [
            phrase for phrase in positive_phrases if phrase in text and f"不{phrase}" not in text
        ]
        decisions = {decision for decision, _ in explicit}
        if independent_positive:
            decisions.add(FeedbackDecision.PASS)
        elif FeedbackDecision.PASS in decisions:
            decisions.remove(FeedbackDecision.PASS)
        if len(decisions) > 1:
            classification = FeedbackClassification(
                decision=FeedbackDecision.UNCLEAR,
                reason="Conflicting explicit feedback phrases",
                confidence=0.5,
                requires_human_confirmation=True,
            )
            return FeedbackClassificationResult(classification=classification, usage=AIUsage())

        patterns = (
            (FeedbackDecision.FAIL, negative_phrases),
            (FeedbackDecision.PASS, tuple(independent_positive)),
            (FeedbackDecision.HOLD, hold_phrases),
        )
        for decision, phrases in patterns:
            for phrase in phrases:
                if phrase in text:
                    classification = FeedbackClassification(
                        decision=decision,
                        reason=f"Explicit feedback phrase: {phrase}",
                        evidence_quote=phrase,
                        confidence=0.98,
                        requires_human_confirmation=True,
                    )
                    return FeedbackClassificationResult(
                        classification=classification, usage=AIUsage()
                    )
        classification = FeedbackClassification(
            decision=FeedbackDecision.UNCLEAR,
            reason="No explicit hiring-stage decision was found",
            confidence=0.9,
            requires_human_confirmation=True,
        )
        return FeedbackClassificationResult(classification=classification, usage=AIUsage())
