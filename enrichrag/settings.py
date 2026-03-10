"""Centralized settings via pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = ""
    tavily_api_key: str = ""
    pubmed_email: str = "your@email.com"
    llm_model: str = "gpt-4o"
    log_level: str = "INFO"
    server_host: str = "127.0.0.1"
    server_port: int = 9001


settings = Settings()

__all__ = ["Settings", "settings"]
