from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)  # src/.env


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # безвредно; в Docker всё равно берём из ENV
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(..., env="BOT_TOKEN")
    api_gateway_url: AnyHttpUrl = Field("http://api-gateway:8080", env="API_GATEWAY_URL")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # читаем из BOT_* (и на всякий случай из старых имён)
    webhook_base: AnyHttpUrl = Field(..., env=["BOT_WEBHOOK_BASE", "WEBHOOK_BASE"])
    webhook_path: str = Field("/tg-webhook", env=["BOT_WEBHOOK_PATH", "WEBHOOK_PATH"])
    webhook_secret: str = Field(..., env=["BOT_WEBHOOK_SECRET", "WEBHOOK_SECRET"])
    web_host: str = Field("0.0.0.0", env=["BOT_WEB_HOST", "WEB_HOST"])
    web_port: int = Field(8081, env=["BOT_WEB_PORT", "WEB_PORT"])

    class Config:  # noqa: D106
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
