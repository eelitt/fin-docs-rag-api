from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, ContentSettings


class AzureBlobStore:
    def __init__(self, account: str, container: str, credential: str | object) -> None:
        self._container = container
        service = BlobServiceClient(
            account_url=f"https://{account}.blob.core.windows.net",
            credential=credential,
        )
        self._client = service.get_container_client(container)

    def ensure_container(self) -> None:
        try:
            self._client.create_container()
        except ResourceExistsError:
            return

    def put(self, name: str, data: bytes) -> None:
        media = "application/json" if name.endswith(".json") else "application/pdf"
        self._client.upload_blob(
            name,
            data,
            overwrite=True,
            content_settings=ContentSettings(content_type=media),
        )

    def get(self, name: str) -> bytes:
        return self._client.download_blob(name).readall()
