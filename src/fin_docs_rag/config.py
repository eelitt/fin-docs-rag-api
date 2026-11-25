import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Settings:
    openai_endpoint: str
    openai_api_key: str
    chat_deployment: str
    embedding_deployment: str
    search_endpoint: str
    search_api_key: str
    storage_account: str
    storage_container: str
    storage_key: str
    key_vault_url: str
    index_name: str = "chunks"


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def settings_from_env() -> Settings:
    def need(name: str) -> str:
        value = os.environ.get(name, "").strip()
        if not value:
            raise ConfigError(f"{name} is not set")
        return value

    return Settings(
        openai_endpoint=need("AZURE_OPENAI_ENDPOINT"),
        openai_api_key=need("AZURE_OPENAI_API_KEY"),
        chat_deployment=os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT", "").strip(),
        embedding_deployment=need("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        search_endpoint=need("AZURE_SEARCH_ENDPOINT"),
        search_api_key=need("AZURE_SEARCH_API_KEY"),
        storage_account=need("AZURE_STORAGE_ACCOUNT"),
        storage_container=need("AZURE_STORAGE_CONTAINER"),
        storage_key=os.environ.get("AZURE_STORAGE_KEY", "").strip(),
        key_vault_url=os.environ.get("AZURE_KEY_VAULT_URL", "").strip(),
    )
