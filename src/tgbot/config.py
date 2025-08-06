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

    class Config:  # noqa: D106
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()  # singleton
