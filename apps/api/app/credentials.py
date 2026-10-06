import keyring

SERVICE_NAME = "BaysysTech Atlas"
OPENAI_KEY_NAME = "openai-api-key"
ANTHROPIC_KEY_NAME = "anthropic-api-key"
HERMES_KEY_NAME = "hermes-api-key"


def provider_key_name(provider: str) -> str:
    return {
        "openai": OPENAI_KEY_NAME,
        "anthropic": ANTHROPIC_KEY_NAME,
        "hermes": HERMES_KEY_NAME,
        "hackclub": OPENAI_KEY_NAME,
    }[provider]


def get_secret(name: str) -> str | None:
    return keyring.get_password(SERVICE_NAME, name)


def set_secret(name: str, value: str) -> None:
    keyring.set_password(SERVICE_NAME, name, value)


def delete_secret(name: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, name)
    except keyring.errors.PasswordDeleteError:
        pass
