"""PG eligibility helper (pure Python).

Used by OA-BR-41 (assistantship) and OA-BR-61 (seminars).
"""

PG_PREFIXES = ("M", "PH")


def is_pg(programme):
    if not programme:
        return False
    return programme.strip().upper().startswith(PG_PREFIXES)
