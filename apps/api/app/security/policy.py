from typing import Literal

from app.security_settings import effective_permission_mode

RiskLevel = Literal["safe", "sensitive"]


def requires_human_approval(risk: RiskLevel, *, tool_name: str | None = None) -> bool:
    """Sensitive actions require review unless the local owner opted into unrestricted mode."""
    if tool_name == "outlook_send_mail":
        return True
    if effective_permission_mode() == "unrestricted":
        return False
    return risk == "sensitive"
