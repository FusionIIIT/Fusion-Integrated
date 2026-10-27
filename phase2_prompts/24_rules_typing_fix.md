# Task: Fix ImportError in modules/leave/domain/rules.py

Error:
`ImportError: cannot import name 'frozenset' from 'typing'`
In Python 3.12, `frozenset` is a built-in type. Do NOT import `frozenset` from `typing`. Remove `from typing import frozenset`.

The imports at the top of `modules/leave/domain/rules.py` must be ONLY:
```python
from collections.abc import Iterable
from datetime import date, timedelta
from decimal import Decimal
```
Also remove `pass` from `RuleViolation`:
```python
class RuleViolation(ValueError):
    """Raised when a leave rule is violated."""
```

Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
