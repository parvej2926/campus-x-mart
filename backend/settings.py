from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_ENV: Literal["dev", "test", "prod"] = "dev"
    DATABASE_URL: str = Field(..., min_length=1)
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_EXPIRES_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    LLM_PROVIDER: Literal["ollama", "openai"] = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral:latest"
    OPENAI_API_KEY: Optional[str] = None
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    CLOUDINARY_UPLOAD_PRESET: Optional[str] = None
    EMAIL_PROVIDER: Literal["smtp", "resend"] = "smtp"
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_PHONE: Optional[str] = None
    EXPOSE_DEV_OTP: bool = False

    @property
    def cors_origins_list(self):
        if not self.CORS_ORIGINS:
            return ["http://localhost:5173", "http://127.0.0.1:5173"]
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned in {
            "change-this-development-secret-before-deployment",
            "replace-with-32-plus-character-secret",
        }:
            raise ValueError("JWT_SECRET_KEY must be changed from the placeholder value.")
        if len(cleaned) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long.")
        return cleaned


settings = Settings(_env_file=Path(__file__).resolve().with_name(".env"))
