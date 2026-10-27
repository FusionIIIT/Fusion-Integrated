# Task: fix the import error in modules/leave/domain/state_machine.py (output the COMPLETE file; keep everything else)

pytest fails to import the module:
  modules/leave/domain/state_machine.py:10: in <module>
      from typing import frozenset, tuple
  ImportError: cannot import name 'frozenset' from 'typing'
`frozenset` and `tuple` are Python builtins and must NOT be imported from `typing`. Delete that import line.
The file must start with `from __future__ import annotations` and `from dataclasses import dataclass, field`, using builtin `frozenset[str]` and `tuple[str, ...]` in annotations.
Blank lines must be completely empty. No explanations, no placeholders, no TODOs.
