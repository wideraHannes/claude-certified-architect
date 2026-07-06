from functools import lru_cache
from pathlib import Path

import anthropic
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: SecretStr
    anthropic_base_url: str = "https://router.eu.requesty.ai"

    model_sonnet: str = Field(default="vertex/claude-sonnet-4-6@europe-west1")
    model_opus: str = Field(default="vertex/claude-opus-4-7@europe-west1")
    model_haiku: str = Field(default="vertex/claude-haiku-4-5@europe-west1")
    default_model: str = Field(default="vertex/claude-sonnet-4-6@europe-west1")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


@lru_cache
def get_client() -> anthropic.Anthropic:
    s = get_settings()
    return anthropic.Anthropic(
        base_url=s.anthropic_base_url,
        api_key=s.anthropic_api_key.get_secret_value(),
    )


settings = get_settings()
client = get_client()
