from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, SecretStr, field_validator

from app.credentials import delete_secret, get_secret, provider_key_name, set_secret
from app.provider_settings import ProviderSettings, get_provider_settings, save_provider_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class ProviderUpdate(BaseModel):
    provider: Literal["openai", "anthropic", "hackclub", "hermes"]
    api_key: SecretStr | None = None
    model: str = Field(min_length=1, max_length=120)
    hermes_base_url: str = Field(default="http://127.0.0.1:8642/v1", max_length=500)

    @field_validator("hermes_base_url")
    @classmethod
    def validate_hermes_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Hermes must use an HTTP endpoint on this machine.")
        return value.rstrip("/")


def _response() -> dict[str, str | bool]:
    settings = get_provider_settings()
    key_name = provider_key_name(settings.provider)
    return {
        "provider": settings.provider,
        "model": settings.model,
        "hermes_base_url": settings.hermes_base_url,
        "configured": bool(get_secret(key_name)),
    }


@router.get("/provider")
def provider_status() -> dict[str, str | bool]:
    return _response()


@router.get("/provider/key-status")
def provider_key_status(provider: Literal["openai", "anthropic", "hackclub", "hermes"]) -> dict[str, bool]:
    return {"configured": bool(get_secret(provider_key_name(provider)))}


@router.put("/provider")
def update_provider(payload: ProviderUpdate) -> dict[str, str | bool]:
    settings = ProviderSettings(
        provider=payload.provider,
        model=payload.model.strip(),
        hermes_base_url=payload.hermes_base_url,
    )
    key_name = provider_key_name(settings.provider)
    if payload.api_key and payload.api_key.get_secret_value().strip():
        set_secret(key_name, payload.api_key.get_secret_value().strip())
    elif not get_secret(key_name):
        label = {"hermes": "Hermes API key", "anthropic": "Anthropic API key"}.get(settings.provider, "AI provider API key")
        raise HTTPException(status_code=422, detail=f"Enter an {label} to configure this provider.")
    save_provider_settings(settings)
    return _response()


@router.delete("/provider/key")
def remove_provider_key() -> dict[str, bool]:
    settings = get_provider_settings()
    key_name = provider_key_name(settings.provider)
    delete_secret(key_name)
    return {"configured": False}
