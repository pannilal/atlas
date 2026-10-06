import os
import shutil
import winreg
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/integrations", tags=["integrations"])


def _outlook_executable() -> Path | None:
    found = shutil.which("OUTLOOK.EXE") or shutil.which("outlook.exe")
    if found:
        return Path(found)
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\OUTLOOK.EXE") as key:
                candidate, _ = winreg.QueryValueEx(key, None)
                if Path(candidate).is_file():
                    return Path(candidate)
        except OSError:
            continue
    for root_var in ("PROGRAMFILES", "PROGRAMFILES(X86)"):
        root = os.environ.get(root_var)
        if root:
            candidate = Path(root, "Microsoft Office", "root", "Office16", "OUTLOOK.EXE")
            if candidate.is_file():
                return candidate
    return None


@router.get("/outlook/status")
def outlook_status() -> dict[str, object]:
    executable = _outlook_executable()
    return {
        "installed": executable is not None,
        "product": "classic_outlook",
        "capabilities": ["search_inbox", "search_sent_items", "send_after_explicit_approval"],
        "send_always_requires_approval": True,
        "read_only": False,
        "note": "Uses the current Windows user's classic Outlook mail profile. New Outlook is not supported by this local COM integration.",
    }
