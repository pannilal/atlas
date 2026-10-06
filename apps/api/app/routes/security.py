from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.security_settings import UNRESTRICTED_ACKNOWLEDGEMENT_VERSION, SecuritySettings, effective_permission_mode, get_security_settings, save_security_settings

router = APIRouter(prefix="/settings/security", tags=["security"])


class SecurityUpdate(BaseModel):
    permission_mode: Literal["review", "unrestricted"]
    acknowledge_unrestricted_risks: bool = False


@router.get("")
def get_security_mode() -> dict[str, object]:
    settings = get_security_settings()
    return {"permission_mode": effective_permission_mode(settings), "reconfirmation_required": settings.permission_mode == "unrestricted" and effective_permission_mode(settings) != "unrestricted"}


@router.put("")
def update_security_mode(payload: SecurityUpdate) -> dict[str, object]:
    if payload.permission_mode == "unrestricted" and not payload.acknowledge_unrestricted_risks:
        raise HTTPException(status_code=422, detail="Confirm that you understand the unrestricted-access risks before enabling it.")
    settings = SecuritySettings(permission_mode=payload.permission_mode, unrestricted_acknowledgement_version=UNRESTRICTED_ACKNOWLEDGEMENT_VERSION if payload.permission_mode == "unrestricted" else 0)
    save_security_settings(settings)
    return {"permission_mode": effective_permission_mode(settings), "reconfirmation_required": False}
