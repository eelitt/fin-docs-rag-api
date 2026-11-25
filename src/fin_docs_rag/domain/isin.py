import re

# Two letters, nine alphanumerics, one check digit. Letters are matched after uppercasing.
_ISIN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")


def is_isin(value: str) -> bool:
    return bool(_ISIN.fullmatch(value)) and _checksum_ok(value)


def isins_in(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _ISIN.findall(text.upper()):
        if match in seen or not _checksum_ok(match):
            continue
        seen.add(match)
        found.append(match)
    return found


def _checksum_ok(isin: str) -> bool:
    digits: list[int] = []
    for char in isin:
        if char.isdigit():
            digits.append(int(char))
            continue
        number = ord(char) - ord("A") + 10
        digits.append(number // 10)
        digits.append(number % 10)
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0
