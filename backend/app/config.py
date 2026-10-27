from pydantic import HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    qdrant_url: HttpUrl | None = None
    qdrant_api_key: SecretStr = SecretStr("")
    generation_model: str = "gpt-5.4-mini-2026-03-17"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384

    # An empty template value should mean "not configured", rather than an invalid URL.
    @field_validator("qdrant_url", mode="before")
    @classmethod
    def empty_url_is_unconfigured(cls, value):
        return None if isinstance(value, str) and not value.strip() else value
