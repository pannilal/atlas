import os
from pathlib import Path

from pydantic import BaseModel


_SETTINGS_FILE = Path(__file__).resolve().parents[1] / "atlas_memory.json"


class MemoryPreferences(BaseModel):
    auto_extract_completed_tasks: bool = False


def get_memory_preferences() -> MemoryPreferences:
    try:
        return MemoryPreferences.model_validate_json(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return MemoryPreferences()


def save_memory_preferences(preferences: MemoryPreferences) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = _SETTINGS_FILE.with_suffix(".json.tmp")
    temporary.write_text(preferences.model_dump_json(indent=2), encoding="utf-8")
    os.replace(temporary, _SETTINGS_FILE)
