from pathlib import Path

from dotenv import load_dotenv
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)  # src/.env


class Settings(BaseSettings):
    bot_token: str = Field(..., env="BOT_TOKEN")

    api_gateway_url: AnyHttpUrl = Field("http://localhost:8080", env="API_GATEWAY_URL")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    webhook_base: AnyHttpUrl = Field(..., env="WEBHOOK_BASE")
    webhook_path: str = Field("/tg-webhook", env="WEBHOOK_PATH")
    webhook_secret: str = Field(..., env="WEBHOOK_SECRET")
    web_host: str = Field("0.0.0.0", env="WEB_HOST")
    web_port: int = Field(8081, env="WEB_PORT")

    class Config:  # noqa: D106
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # singleton
