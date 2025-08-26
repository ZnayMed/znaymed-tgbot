# tgbot/config.py
from functools import lru_cache
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra="ignore",
        # убрали env_file и env_file_encoding
    )

    bot_token: str = Field(..., env="BOT_TOKEN")
    api_gateway_url: AnyHttpUrl = Field("http://api-gateway:8080", env="API_GATEWAY_URL")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    webhook_base: str = Field(..., env=["BOT_WEBHOOK_BASE", "WEBHOOK_BASE"])
    webhook_path: str = Field("/tg-webhook", env=["BOT_WEBHOOK_PATH", "WEBHOOK_PATH"])
    # секрет делаем необязательным: можно запускать и без него (для локалки),
    # а если задан — используем
    webhook_secret: str = Field("", env=["BOT_WEBHOOK_SECRET", "WEBHOOK_SECRET"])
    web_host: str = Field("0.0.0.0", env=["BOT_WEB_HOST", "WEB_HOST"])
    web_port: int = Field(8081, env=["BOT_WEB_PORT", "WEB_PORT"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
