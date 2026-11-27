from fin_docs_rag.domain.models import (
    COST_COLUMNS,
    NUMERIC_COLUMNS,
    Citation,
    SheetCell,
    cell_from_dict,
)

_LABEL = {
    "ongoing_charge": "ongoing cost",
    "sri": "risk indicator",
    "holding_period": "recommended holding period",
    "entry_cost": "entry cost",
    "exit_cost": "exit cost",
}
_UNIT = {
    "ongoing_charge": "percentage points",
    "entry_cost": "percentage points",
    "exit_cost": "percentage points",
    "sri": "risk-indicator steps",
    "holding_period": "years",
}


def format_number(value: float) -> str:
    text = f"{round(value, 4):.4f}".rstrip("0").rstrip(".")
    if text in ("-0", ""):
        return "0"
    return text


def lookup_sentence(isin: str, field: str, cell: SheetCell, holding: SheetCell | None) -> str:
    label = _LABEL[field]
    if cell.state == "not_stated":
        return f"{isin} has no stated {label}."
    if cell.state != "stated" or cell.quote is None:
        return f"{isin} {label} was not extracted."
    if field in NUMERIC_COLUMNS and cell.number is not None:
        sentence = f"The {label} for {isin} is {format_number(cell.number)} ({cell.quote})."
    else:
        sentence = f"The {label} for {isin} is {cell.quote}."
    if field not in COST_COLUMNS:
        return sentence
    if holding is not None and holding.state == "stated" and holding.quote:
        if holding.quote.endswith("."):
            return f"{sentence} The figure assumes {holding.quote}"
        return f"{sentence} The figure assumes {holding.quote}."
    return f"{sentence} The holding period is not stated."


def compare_sentence(
    isin_a: str,
    cell_a: SheetCell | None,
    isin_b: str,
    cell_b: SheetCell | None,
    field: str,
    holding_a: SheetCell | None,
    holding_b: SheetCell | None,
) -> str:
    gap_a = _gap(isin_a, cell_a, field)
    gap_b = _gap(isin_b, cell_b, field)
    if gap_a or gap_b:
        parts = []
        if gap_a:
            parts.append(gap_a)
        elif cell_a is not None and cell_a.state == "stated" and cell_a.number is not None:
            parts.append(f"{isin_a} states {format_number(cell_a.number)} ({cell_a.quote}).")
        if gap_b:
            parts.append(gap_b)
        elif cell_b is not None and cell_b.state == "stated" and cell_b.number is not None:
            parts.append(f"{isin_b} states {format_number(cell_b.number)} ({cell_b.quote}).")
        return " ".join(parts)
    return " ".join(
        (
            f"{isin_a} states {format_number(cell_a.number)} ({cell_a.quote}).",
            f"{isin_b} states {format_number(cell_b.number)} ({cell_b.quote}).",
            _period(isin_a, holding_a),
            _period(isin_b, holding_b),
            (
                f"The difference, {isin_a} minus {isin_b}, is "
                f"{format_number(cell_a.number - cell_b.number)} {_UNIT[field]}."
            ),
        )
    )


def ongoing_comparison(sheet: dict, isin_a: str, isin_b: str) -> dict:
    rows = {row["isin"]: row for row in sheet["funds"]}
    row_a = rows.get(isin_a)
    row_b = rows.get(isin_b)
    cell_a = None if row_a is None else cell_from_dict(row_a["ongoing_charge"])
    cell_b = None if row_b is None else cell_from_dict(row_b["ongoing_charge"])
    holding_a = None if row_a is None else cell_from_dict(row_a["holding_period"])
    holding_b = None if row_b is None else cell_from_dict(row_b["holding_period"])
    return {
        "isin_a": isin_a,
        "isin_b": isin_b,
        "field": "ongoing_charge",
        "sentence": compare_sentence(isin_a, cell_a, isin_b, cell_b, "ongoing_charge", holding_a, holding_b),
        "cell_a": None if cell_a is None else cell_a.to_dict(),
        "cell_b": None if cell_b is None else cell_b.to_dict(),
    }


def cited(cell: SheetCell | None) -> list[Citation]:
    if cell is None or cell.citation is None:
        return []
    return [cell.citation]


def _gap(isin: str, cell: SheetCell | None, field: str) -> str | None:
    label = _LABEL[field]
    if cell is None:
        return f"{isin} is not on the sheet."
    if cell.state == "not_stated":
        return f"{isin} has no stated {label}."
    if cell.state != "stated" or cell.number is None or cell.quote is None:
        return f"{isin} {label} was not extracted."
    return None


def _period(isin: str, holding: SheetCell | None) -> str:
    if holding is not None and holding.state == "stated" and holding.quote:
        if holding.quote.endswith("."):
            return f"The figure for {isin} assumes {holding.quote}"
        return f"The figure for {isin} assumes {holding.quote}."
    return f"The figure for {isin} assumes a holding period that is not stated."
