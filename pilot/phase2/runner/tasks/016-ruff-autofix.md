TITLE: Apply ruff format and ruff's safe autofixes to the leave module
FORMAT: whole
EDIT: modules/leave/__init__.py
LIMIT: 300
POST: ruff
---
Fusion's CI runs `ruff check .` with the rule set in pyproject.toml, and the leave module has about 90 findings, most of them mechanical (blank lines containing whitespace, import order, unnecessary f-strings, long lines). The task runner fixes those with the SE tools themselves right after this step (ruff format + ruff check --fix, safe fixes only), so no other code change is needed from you.

Your only job: make modules/leave/__init__.py contain exactly this one line and nothing else:
"""Employee Leave Management (ELM) module for Fusion."""
