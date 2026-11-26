from pathlib import Path

from fin_docs_rag.composition import build_app
from fin_docs_rag.config import load_env_file, settings_from_env

load_env_file(Path.cwd() / ".env")
app = build_app(settings_from_env())
