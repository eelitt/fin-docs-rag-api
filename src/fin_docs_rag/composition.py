import json
from pathlib import Path

from fin_docs_rag.adapters.blob_store import AzureBlobStore
from fin_docs_rag.adapters.openai_chat import OpenAIChat
from fin_docs_rag.adapters.openai_embed import OpenAIEmbedder
from fin_docs_rag.adapters.prompts import FilePrompts
from fin_docs_rag.adapters.search import AzureSearch
from fin_docs_rag.adapters.telemetry import Telemetry
from fin_docs_rag.config import ConfigError, Settings
from fin_docs_rag.http.app import create_app
from fin_docs_rag.pipeline import AskDeps, answer_question
from fin_docs_rag.ports import DependencyFailure


def build_ingest(settings: Settings) -> tuple[AzureBlobStore, OpenAIEmbedder, AzureSearch]:
    login = _login() if _needs_login(settings) else None
    if settings.storage_key:
        blob_credential: str | object = settings.storage_key
    else:
        blob_credential = login
    return (
        AzureBlobStore(settings.storage_account, settings.storage_container, blob_credential),
        OpenAIEmbedder(
            settings.openai_endpoint,
            settings.openai_api_key,
            settings.embedding_deployment,
            None if settings.openai_api_key else _token(login),
        ),
        AzureSearch(settings.search_endpoint, settings.search_api_key or login, settings.index_name),
    )


def build_chat(settings: Settings) -> OpenAIChat:
    if not settings.chat_deployment:
        raise ConfigError("AZURE_OPENAI_CHAT_DEPLOYMENT is not set")
    root = Path(__file__).resolve().parents[2] / "prompts"
    token_provider = None if settings.openai_api_key else _token(_login())
    return OpenAIChat(
        settings.openai_endpoint,
        settings.openai_api_key,
        settings.chat_deployment,
        FilePrompts(root),
        token_provider,
    )


def _needs_login(settings: Settings) -> bool:
    return not settings.storage_key or not settings.openai_api_key or not settings.search_api_key


def _login():
    import logging

    from azure.core.exceptions import ClientAuthenticationError
    from azure.identity import DefaultAzureCredential

    logging.getLogger("azure.identity").setLevel(logging.CRITICAL)
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    try:
        credential.get_token("https://storage.azure.com/.default")
    except ClientAuthenticationError:
        raise ConfigError(
            "Blob upload has no Azure login. Add AZURE_STORAGE_KEY to .env "
            "(storage account, Security + networking, Access keys, key1), "
            "or sign in with Azure CLI."
        ) from None
    return credential


def _token(credential):
    from azure.identity import get_bearer_token_provider

    return get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")


def build_ask_deps(settings: Settings) -> AskDeps:
    blob, embedder, search = build_ingest(settings)
    chat = build_chat(settings)
    try:
        sheet = json.loads(blob.get("sheet.json"))
    except Exception as error:
        raise DependencyFailure("sheet") from error
    if not isinstance(sheet, dict) or not isinstance(sheet.get("funds"), list):
        raise DependencyFailure("sheet")
    return AskDeps(chat=chat, embedder=embedder, search=search, sheet=sheet)


def build_app(settings: Settings):
    blob, embedder, search = build_ingest(settings)
    chat = build_chat(settings)

    def read_sheet() -> dict:
        try:
            data = json.loads(blob.get("sheet.json"))
        except Exception as error:
            raise DependencyFailure("sheet") from error
        if not isinstance(data, dict) or not isinstance(data.get("funds"), list):
            raise DependencyFailure("sheet")
        return data

    def ping() -> None:
        try:
            search.ping()
        except Exception as error:
            raise DependencyFailure("search") from error

    def ask(envelope):
        return answer_question(
            envelope,
            AskDeps(chat=chat, embedder=embedder, search=search, sheet=read_sheet()),
        )

    return create_app(
        read_sheet=read_sheet,
        ping=ping,
        ask=ask,
        write_trace=Telemetry(settings.app_insights_connection_string).write,
    )
