from pathlib import Path

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: SecretStr = SecretStr("")
    qdrant_url: HttpUrl | None = None
    qdrant_api_key: SecretStr = SecretStr("")
    generation_model: str = "gpt-5.4-mini-2026-03-17"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = Field(default=384, ge=1, le=1536)
    retrieval_strategy: str = Field(default="a", pattern="^[ab]$")
    usage_db: Path = Path("data/usage.sqlite3")
    api_budget_usd: float = Field(default=4.5, gt=0, le=5)
    embedding_usd_per_million: float = Field(default=0.02, gt=0)
    generation_input_usd_per_million: float = Field(default=0.75, gt=0)
    generation_output_usd_per_million: float = Field(default=4.5, gt=0)
    demo_admin_token: SecretStr = SecretStr("")
    document_collection_prefix: str = Field(
        default="investigation", pattern=r"^[a-zA-Z0-9_-]{1,48}$"
    )

    # An empty template value should mean "not configured", rather than an invalid URL.
    @field_validator("qdrant_url", mode="before")
    @classmethod
    def empty_url_is_unconfigured(cls, value):
        return None if isinstance(value, str) and not value.strip() else value
