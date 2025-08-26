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

    # --- webhook settings (с префиксом BOT_) ---
    webhook_base: AnyHttpUrl = Field(..., env="BOT_WEBHOOK_BASE")
    webhook_path: str = Field("/tg-webhook", env="BOT_WEBHOOK_PATH")
    webhook_secret: str = Field(..., env="BOT_WEBHOOK_SECRET")
    web_host: str = Field("0.0.0.0", env="BOT_WEB_HOST")
    web_port: int = Field(8081, env="BOT_WEB_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # singleton
