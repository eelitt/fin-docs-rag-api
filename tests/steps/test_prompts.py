from pathlib import Path

from fin_docs_rag.adapters.prompts import FilePrompts

_ROOT = Path(__file__).resolve().parents[2] / "prompts"


def test_prompt_files_load_by_id():
    prompts = FilePrompts(_ROOT)
    for prompt_id in ("router_v1", "grade_v1", "answer_v1", "extract_v1"):
        text = prompts.load(prompt_id)
        assert "ongoing_charge" in text or prompt_id != "router_v1"
        assert text.strip()
