import os
from pathlib import Path

import pytest

from src.ai import create_ai_provider
from src.config import Settings


pytestmark = [
    pytest.mark.live_ai,
    pytest.mark.skipif(
        os.getenv("RUN_LIVE_AI_TESTS") != "1",
        reason="set RUN_LIVE_AI_TESTS=1 to run live AI tests",
    ),
]


def test_live_anonymized_resume_extraction() -> None:
    settings = Settings(ai_mode="real")
    provider = create_ai_provider(settings)
    text = Path("samples/anonymous-resume.txt").read_text(encoding="utf-8")

    result = provider.extract_candidate(text, "", [])
    draft = result.draft

    assert draft.name == "林晓"
    assert draft.education[0]["school"] == "示例大学"
    assert draft.field_sources["name"].quote
    assert result.usage.total_tokens > 0
