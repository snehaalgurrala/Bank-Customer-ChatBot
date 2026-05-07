from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "AI Customer Loan Assistance Chatbot"
    environment: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    frontend_api_url: str = "http://127.0.0.1:8000"

    database_url: str = "sqlite:///./database/chatbot.db"
    upload_dir: Path = Path("./uploads")
    vectorstore_dir: Path = Path("./vectorstore/chroma")
    sample_data_dir: Path = Path("./sample_data")

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_site_url: str = "http://localhost"
    openrouter_app_name: str = "Loan Assistance Chatbot"
    jwt_secret_key: str = "change-this-local-development-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def ensure_directories(self) -> None:
        for path in (self.upload_dir, self.vectorstore_dir, self.sample_data_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
