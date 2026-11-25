import re
from dataclasses import dataclass

import pymupdf


class NoTextLayer(Exception):
    """The PDF has no extractable text. v1 does not OCR it."""


@dataclass(frozen=True)
class PdfPage:
    number: int
    text: str


def parse_pdf(data: bytes) -> list[PdfPage]:
    document = pymupdf.open(stream=data, filetype="pdf")
    pages = []
    for index, page in enumerate(document, start=1):
        text = _page_text(page)
        if text:
            pages.append(PdfPage(number=index, text=text))
    if not pages:
        raise NoTextLayer("PDF has no text layer")
    return pages


def _page_text(page: pymupdf.Page) -> str:
    blocks = [block for block in page.get_text("blocks") if block[6] == 0 and block[4].strip()]
    lines = [_block_text(block[4]) for block in _reading_order(blocks)]
    return "\n".join(line for line in lines if line)


def _block_text(raw: str) -> str:
    # A hyphen at the end of a visual line is a line-break hyphen, not a word hyphen.
    joined = re.sub(r"-\s*\n\s*", "", raw.replace("\r", ""))
    return " ".join(joined.split())


def _reading_order(blocks: list[tuple]) -> list[tuple]:
    split = _column_split(blocks)
    if split is None:
        return sorted(blocks, key=lambda block: (block[1], block[0]))
    spanning = []
    left = []
    right = []
    for block in blocks:
        if block[0] < split < block[2]:
            spanning.append(block)
        elif (block[0] + block[2]) / 2 < split:
            left.append(block)
        else:
            right.append(block)
    spanning.sort(key=lambda block: block[1])
    left.sort(key=lambda block: block[1])
    right.sort(key=lambda block: block[1])
    # Above each full-width block, read the left column and then the right column.
    ordered = []
    left_index = 0
    right_index = 0
    for span in spanning + [None]:
        cut = span[1] if span is not None else float("inf")
        while left_index < len(left) and left[left_index][1] < cut:
            ordered.append(left[left_index])
            left_index += 1
        while right_index < len(right) and right[right_index][1] < cut:
            ordered.append(right[right_index])
            right_index += 1
        if span is not None:
            ordered.append(span)
    return ordered


def _column_split(blocks: list[tuple]) -> float | None:
    if len(blocks) < 6:
        return None
    left_edge = min(block[0] for block in blocks)
    right_edge = max(block[2] for block in blocks)
    span = right_edge - left_edge
    if span <= 0:
        return None
    narrow = [block for block in blocks if (block[2] - block[0]) < span * 0.6]
    if len(narrow) < 6:
        return None
    centers = sorted((block[0] + block[2]) / 2 for block in narrow)
    best_gap = 0.0
    split = None
    for earlier, later in zip(centers, centers[1:]):
        gap = later - earlier
        midpoint = (earlier + later) / 2
        if gap < 24:
            continue
        if not (left_edge + span * 0.3 < midpoint < left_edge + span * 0.7):
            continue
        if gap > best_gap:
            best_gap = gap
            split = midpoint
    if split is None:
        return None
    left = sum(1 for center in centers if center < split)
    right = len(centers) - left
    if left < 3 or right < 3:
        return None
    return split
