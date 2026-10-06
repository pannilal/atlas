import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

_SETTINGS_FILE = Path(__file__).resolve().parents[1] / "atlas_security.json"
UNRESTRICTED_ACKNOWLEDGEMENT_VERSION = 4


class SecuritySettings(BaseModel):
    permission_mode: Literal["review", "unrestricted"] = "review"
    unrestricted_acknowledgement_version: int = 0


def get_security_settings() -> SecuritySettings:
    try:
        return SecuritySettings.model_validate_json(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return SecuritySettings()


def save_security_settings(settings: SecuritySettings) -> None:
    _SETTINGS_FILE.write_text(settings.model_dump_json(indent=2), encoding="utf-8")


def effective_permission_mode(settings: SecuritySettings | None = None) -> Literal["review", "unrestricted"]:
    current = settings or get_security_settings()
    if current.permission_mode == "unrestricted" and current.unrestricted_acknowledgement_version >= UNRESTRICTED_ACKNOWLEDGEMENT_VERSION:
        return "unrestricted"
    return "review"
