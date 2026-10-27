# Task: Fix line length in modules/leave/services/applications.py

In `modules/leave/services/applications.py`, split:
```python
            if application.status in (
                sm.AWAITING_ESTABLISHMENT, sm.CANCELLATION_PENDING_ESTABLISHMENT
            ):
                return sm.ESTABLISHMENT
```
Ensure all lines in the file are strictly <= 100 characters.
Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
