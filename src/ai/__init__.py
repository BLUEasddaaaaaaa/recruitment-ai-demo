from src.ai.fake_provider import FakeAIProvider
from src.ai.openai_provider import OpenAIProvider
from src.ai.protocol import AIProvider
from src.config import Settings


class AIConfigurationError(RuntimeError):
    """Raised when real provider construction lacks validated settings."""


def create_ai_provider(settings: Settings) -> AIProvider:
    if settings.ai_mode == "fake":
        return FakeAIProvider()
    if settings.openai_api_key is None or settings.openai_model is None:
        raise AIConfigurationError("Real AI configuration is incomplete")
    return OpenAIProvider(
        model=settings.openai_model,
        api_key=settings.openai_api_key.get_secret_value(),
    )


__all__ = [
    "AIConfigurationError",
    "AIProvider",
    "FakeAIProvider",
    "OpenAIProvider",
    "create_ai_provider",
]
