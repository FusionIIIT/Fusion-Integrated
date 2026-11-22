_ALIASES = {
    "computer science": "cse",
    "computer science engineering": "cse",
    "electronics and communication": "ece",
    "electronics and communication engineering": "ece",
    "mechanical engineering": "me",
    "natural sciences": "ns",
}


def department_code(value: str) -> str:
    normalized = " ".join(value.strip().casefold().split())
    return _ALIASES.get(normalized, normalized)
