import hashlib
import json
import os
from pathlib import Path

from fin_docs_rag.domain.models import RequestEnvelope
from fin_docs_rag.eval.score import OUTCOMES, PATHS, summarize
from fin_docs_rag.pipeline import AskDeps, answer_question

QUESTION_TYPES = ("fact", "comparison", "absence", "advice", "long_document")
REASONS = ("advice_refused", "not_in_corpus", "ungrounded")


def golden_path() -> Path:
    return Path(__file__).resolve().parents[3] / "eval" / "golden.json"


def load_golden(path: Path | None = None) -> dict:
    data = json.loads((path or golden_path()).read_text(encoding="utf-8"))
    _validate(data)
    return data


def run_items(golden: dict, deps: AskDeps) -> dict:
    answers = []
    for item in golden["items"]:
        answers.append(
            answer_question(
                RequestEnvelope(item["id"], "demo", tuple(item["instrument_ids"]), item["question"]),
                deps,
            )
        )
    return summarize(golden["items"], answers, deps.sheet, golden["k"], golden["version"])


def prompt_versions(prompt_dir: Path) -> dict[str, str]:
    versions = {}
    for path in sorted(prompt_dir.glob("*.md")):
        versions[path.stem] = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return versions


def main() -> None:
    from fin_docs_rag.adapters.mlflow_log import log_run
    from fin_docs_rag.composition import build_ask_deps
    from fin_docs_rag.config import load_env_file, settings_from_env

    root = Path(__file__).resolve().parents[3]
    load_env_file(root / ".env")
    golden = load_golden()
    report = run_items(golden, build_ask_deps(settings_from_env()))
    log_run(report, prompt_versions(root / "prompts"), os.environ.get("MLFLOW_TRACKING_URI", "file:./mlruns"))
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


def _validate(data: dict) -> None:
    if data.get("k") != 8 or not isinstance(data.get("version"), str) or not data["version"]:
        raise ValueError("golden file needs version and k 8")
    items = data.get("items")
    if not isinstance(items, list) or not 25 <= len(items) <= 40:
        raise ValueError("golden file needs 25 to 40 items")
    ids: set[str] = set()
    questions: set[str] = set()
    types: set[str] = set()
    for item in items:
        if item["id"] in ids or item["question"] in questions:
            raise ValueError(f"duplicate golden item {item['id']}")
        ids.add(item["id"])
        questions.add(item["question"])
        if item["path"] not in PATHS or item["question_type"] not in QUESTION_TYPES:
            raise ValueError(f"{item['id']} has a bad path or question type")
        types.add(item["question_type"])
        kind = item["outcome"]["kind"]
        value = item["outcome"]["value"]
        if kind not in OUTCOMES:
            raise ValueError(f"{item['id']} has a bad outcome")
        if kind == "reason" and value not in REASONS:
            raise ValueError(f"{item['id']} has a bad reason")
        if item["path"] == "refuse" and (kind != "reason" or value != "advice_refused"):
            raise ValueError(f"{item['id']} refuses without advice_refused")
        if item["path"] == "sheet" and "field" not in item:
            raise ValueError(f"{item['id']} is a sheet item without a field")
        chunk_id = item.get("chunk_id")
        if chunk_id and kind == "source" and not chunk_id.startswith(f"{value}:"):
            raise ValueError(f"{item['id']} names a chunk from another source")
    if types != set(QUESTION_TYPES):
        raise ValueError("golden file is missing a question type")
