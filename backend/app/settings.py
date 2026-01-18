from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic import field_validator

load_dotenv()


class Settings(BaseSettings):
    MP_ACCESS_TOKEN: str = ""
    MP_WEBHOOK_SECRET: str = ""
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    MP_NOTIFICATION_URL: str = ""

    DB_PATH: str = "./backend/app.db"
    ADMIN_TOKEN: str = ""

    ALLOWED_ORIGINS: str = "http://localhost:3000"
    ALLOWED_METHODS: str = "GET,POST,OPTIONS"
    ALLOWED_HEADERS: str = "Content-Type,Authorization,X-Admin-Token"

    DEFAULT_CURRENCY: str = "ARS"
    QUOTE_TTL_SECONDS: int = 900

    # IMPORTANT: tu UI permite grandes cantidades -> subir el default y dejarlo configurable por env
    MAX_QTY_PER_FIELD: int = Field(default=500_000_000, ge=0)

    GROUP_ITEMS_FOR_MP: bool = True

    # precios en centavos (ints)
    PRICE_FOLLOW_CENTS: int = 10
    PRICE_LIKE_CENTS: int = 5
    PRICE_VIEW_CENTS: int = 1
    PRICE_COMMENT_CENTS: int = 8

    LOG_LEVEL: str = "INFO"

    IG_USER: str = ""
    IG_PASS: str = ""
    IG_SETTINGS_PATH: str = "./backend/ig_settings.json"

    model_config = {
        "env_file": os.getenv("ENV_FILE", ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("ALLOWED_ORIGINS", "ALLOWED_METHODS", "ALLOWED_HEADERS")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    def list_from_csv(self, value: str) -> List[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def allowed_origins_list(self) -> List[str]:
        return self.list_from_csv(self.ALLOWED_ORIGINS)

    @property
    def allowed_methods_list(self) -> List[str]:
        return self.list_from_csv(self.ALLOWED_METHODS)

    @property
    def allowed_headers_list(self) -> List[str]:
        return self.list_from_csv(self.ALLOWED_HEADERS)

    @property
    def notification_url(self) -> str:
        if self.MP_NOTIFICATION_URL:
            return self.MP_NOTIFICATION_URL
        return f"{self.PUBLIC_BASE_URL.rstrip('/')}/webhooks/mercadopago"


settings = Settings()
