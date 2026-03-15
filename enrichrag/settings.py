"""Centralized settings via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    tavily_api_key: str = ""
    pubmed_email: str = "your@email.com"
    llm_model: str = "gpt-4o"
    llm_model_report: str = "gpt-5.4"
    log_level: str = "INFO"
    server_host: str = "127.0.0.1"
    server_port: int = 9001
    url_prefix: str = ""
    auth_db_path: str = str(Path("~/.enrichrag/app/auth_v2.db").expanduser())
    auth_cookie_name: str = "enrichrag_session"
    auth_default_email: str = "lab@enrichrag.local"
    auth_invite_code: str = "enrichrag-invite"
    auth_default_password: str = "lab-demo-change-me"
    auth_secure_cookies: bool = False
    query_planning_llm_refine: bool = True
    kg_enabled: bool = True
    kg_db_path: str = str(Path("~/.enrichrag/knowledge_graph/data/knowledge_graph.db").expanduser())
    kg_data_dir: str = str(Path("~/.enrichrag/knowledge_graph/data").expanduser())


settings = Settings()

__all__ = ["Settings", "settings"]
