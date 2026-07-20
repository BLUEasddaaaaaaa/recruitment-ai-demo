from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    database_url: str = "sqlite:///data/recruitment.db"
    ai_mode: Literal["fake", "real"] = "fake"
    wecom_webhook_url: str | None = None
    tencent_docs_mode: Literal["mock", "real"] = "mock"

    @field_validator("openai_model")
    @classmethod
    def strip_model(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("openai_api_key")
    @classmethod
    def strip_api_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        return SecretStr(value.get_secret_value().strip())

    @model_validator(mode="after")
    def require_real_ai_configuration(self) -> "Settings":
        has_api_key = bool(self.openai_api_key and self.openai_api_key.get_secret_value().strip())
        if self.ai_mode == "real" and (not has_api_key or not (self.openai_model or "").strip()):
            raise ValueError("OPENAI_API_KEY and OPENAI_MODEL are required when AI_MODE=real")
        return self
