import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

_SETTINGS_FILE = Path(__file__).resolve().parents[1] / "atlas_settings.json"


class ProviderSettings(BaseModel):
    provider: Literal["openai", "anthropic", "hackclub", "hermes"] = "hackclub"
    model: str = "openai/gpt-4o-mini"
    hermes_base_url: str = "http://127.0.0.1:8642/v1"


def get_provider_settings() -> ProviderSettings:
    try:
        return ProviderSettings.model_validate_json(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ProviderSettings()
    except (ValueError, OSError):
        return ProviderSettings()


def save_provider_settings(settings: ProviderSettings) -> None:
    _SETTINGS_FILE.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
