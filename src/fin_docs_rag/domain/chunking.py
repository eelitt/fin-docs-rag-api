import re
from collections.abc import Sequence

import tiktoken

from fin_docs_rag.domain.models import Chunk

KID_SECTION_TOKENS = 1200
KID_OVERLAP_TOKENS = 100
REPORT_SECTION_TOKENS = 800
REPORT_OVERLAP_TOKENS = 120

_ENCODER = tiktoken.get_encoding("cl100k_base")

# Printed PRIIPs headings, Finnish and English. Longer patterns are exact lines.
# Prefixes cover the inability and holding headings, which include the manufacturer
# or wrap onto a second line.
_EXACT_HEADINGS = {
    "tarkoitus": "purpose",
    "tämän asiakirjan tarkoitus": "purpose",
    "purpose": "purpose",
    "tuote": "product",
    "product": "product",
    "mikä tämä tuote on?": "what",
    "what is this product?": "what",
    "mitkä ovat riskit ja mitä tuottoa sijoittaja voi saada?": "risks",
    "what are the risks and what could i get in return?": "risks",
    "mitä kuluja sijoittajalle aiheutuu?": "costs",
    "what are the costs?": "costs",
    "kuinka sijoittaja voi valittaa?": "complaints",
    "how can i complain?": "complaints",
}
_PREFIX_HEADINGS = (
    ("mitä tapahtuu, jos", "inability"),
    ("what happens if", "inability"),
    ("miten pitkäksi aikaa sijoitus olisi tehtävä", "holding"),
    ("how long should i hold it", "holding"),
    ("muut olennaiset tiedot", "other"),
    ("other relevant information", "other"),
)
_LETTERS = re.compile(r"[^\W\d_]", re.UNICODE)


def chunk_document(doc_id: str, pages: Sequence[tuple[int, str]], kind: str) -> list[Chunk]:
    if ":" in doc_id:
        raise ValueError("doc_id must not contain ':'")
    if kind == "kid":
        limit, overlap = KID_SECTION_TOKENS, KID_OVERLAP_TOKENS
        sections = _kid_sections(pages)
    elif kind == "report":
        limit, overlap = REPORT_SECTION_TOKENS, REPORT_OVERLAP_TOKENS
        sections = _report_sections(pages)
    else:
        raise ValueError(f"unknown kind: {kind}")

    chunks: list[Chunk] = []
    for section, page, text in sections:
        for window, piece in enumerate(_windows(text, limit, overlap)):
            chunks.append(
                Chunk(
                    id=f"{doc_id}:{section}:{page}:{window}",
                    doc_id=doc_id,
                    section=section,
                    page=page,
                    window=window,
                    text=piece,
                )
            )
    return chunks


def _kid_sections(pages: Sequence[tuple[int, str]]) -> list[tuple[str, int, str]]:
    section = "preamble"
    blocks: list[tuple[str, int, list[str]]] = []
    for number, text in pages:
        lines = _lines(text)
        index = 0
        while index < len(lines):
            found = _kid_heading(lines, index)
            if found is None:
                _append(blocks, section, number, lines[index])
                index += 1
                continue
            section, consumed = found
            heading = " ".join(lines[index : index + consumed])
            _append(blocks, section, number, heading)
            index += consumed
    return _finish(blocks)


def _kid_heading(lines: list[str], index: int) -> tuple[str, int] | None:
    folded = _fold(lines[index])
    exact = _EXACT_HEADINGS.get(folded)
    if exact is not None:
        return exact, 1
    prefix = _prefix_heading(folded)
    if prefix is not None:
        return prefix, 1
    if index + 1 >= len(lines):
        return None
    joined = folded + " " + _fold(lines[index + 1])
    exact = _EXACT_HEADINGS.get(joined)
    if exact is not None:
        return exact, 2
    prefix = _prefix_heading(joined)
    if prefix is not None:
        return prefix, 2
    return None


def _prefix_heading(folded: str) -> str | None:
    for pattern, key in _PREFIX_HEADINGS:
        if folded.startswith(pattern):
            return key
    return None


def _report_sections(pages: Sequence[tuple[int, str]]) -> list[tuple[str, int, str]]:
    section = "preamble"
    blocks: list[tuple[str, int, list[str]]] = []
    for number, text in pages:
        for line in _lines(text):
            if _is_report_heading(line):
                section = _slug(line)
            _append(blocks, section, number, line)
    return _finish(blocks)


def _is_report_heading(line: str) -> bool:
    if not 4 <= len(line) <= 90:
        return False
    letters = _LETTERS.findall(line)
    if len(letters) < 4:
        return False
    upper = sum(1 for char in letters if char.isupper())
    return upper / len(letters) >= 0.8


def _append(blocks: list[tuple[str, int, list[str]]], section: str, page: int, line: str) -> None:
    if blocks and blocks[-1][0] == section and blocks[-1][1] == page:
        blocks[-1][2].append(line)
        return
    blocks.append((section, page, [line]))


def _finish(blocks: list[tuple[str, int, list[str]]]) -> list[tuple[str, int, str]]:
    finished = []
    for section, page, lines in blocks:
        text = "\n".join(lines).strip()
        if text:
            finished.append((section, page, text))
    return finished


def _windows(text: str, limit: int, overlap: int) -> list[str]:
    if _count(text) <= limit:
        return [text]
    parts = [part for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(parts) == 1:
        parts = [part for part in text.split("\n") if part.strip()]
    windows: list[str] = []
    current: list[str] = []
    for part in parts:
        if _count(part) > limit:
            if current:
                windows.append("\n".join(current))
                current = []
            windows.extend(_hard_windows(part, limit, overlap))
            continue
        if current and _count("\n".join(current + [part])) > limit:
            windows.append("\n".join(current))
            current = _overlap_tail(current, overlap)
        current.append(part)
    if current:
        windows.append("\n".join(current))
    return windows


def _overlap_tail(parts: list[str], overlap: int) -> list[str]:
    tail: list[str] = []
    tokens = 0
    for part in reversed(parts):
        part_tokens = _count(part)
        if tail and tokens + part_tokens > overlap:
            break
        tail.append(part)
        tokens += part_tokens
    tail.reverse()
    return tail


def _hard_windows(text: str, limit: int, overlap: int) -> list[str]:
    tokens = _ENCODER.encode(text)
    windows = []
    start = 0
    while start < len(tokens):
        stop = min(start + limit, len(tokens))
        windows.append(_ENCODER.decode(tokens[start:stop]))
        if stop == len(tokens):
            break
        start = stop - overlap
    return windows


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _fold(text: str) -> str:
    return " ".join(text.casefold().split())


def _slug(text: str) -> str:
    folded = text.translate(str.maketrans("äöåÄÖÅ", "aoaAOA")).casefold()
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return slug[:60] or "section"


def _count(text: str) -> int:
    return len(_ENCODER.encode(text))
