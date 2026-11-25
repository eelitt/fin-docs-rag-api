"""Download the public PDFs listed in sources/manifest.json."""

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "sources" / "manifest.json"
DESTINATION = ROOT / "data" / "pdfs"
REQUIRED = ("id", "title", "publisher", "url", "retrieved", "license_note", "language", "kind", "file", "isins")


def main() -> None:
    documents = json.loads(MANIFEST.read_text(encoding="utf-8"))
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for document in documents:
        missing = [field for field in REQUIRED if field not in document]
        if missing:
            raise SystemExit(f"{document.get('id', '?')} is missing {missing}")
        path = DESTINATION / document["file"]
        if path.is_file() and path.stat().st_size > 0:
            print(f"keep {path.name}")
            continue
        request = urllib.request.Request(document["url"], headers={"User-Agent": "fin-docs-rag"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        if not data.startswith(b"%PDF"):
            raise SystemExit(f"{document['id']} did not return a PDF")
        path.write_bytes(data)
        print(f"saved {path.name} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
