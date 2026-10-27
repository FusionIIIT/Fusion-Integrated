# Task: Clean up modules/leave/services/applications.py for ruff checks

Requirements:
1. Max line length 100 chars (break lines longer than 100 chars cleanly).
2. Remove unused imports (`models` from `django.db`, `DomainError` from `core.api.exceptions`).
3. In `resolve_or_raise`:
   - `except sm.InvalidTransition as exc: raise ConflictError(...) from exc`
   - `except sm.ActorNotAllowed as exc: raise PermissionDeniedError(...) from exc`
   - `except sm.ScopeMismatch as exc: raise ConflictError(...) from exc`
4. In `apply`:
   - `except LeaveCategory.DoesNotExist as exc: raise NotFoundError(...) from exc`
5. In `transition`:
   - Combine nested `if`:
     `if actor is not None and getattr(actor, "has_permission", None) is not None and not actor.has_permission(t.permission):`
6. Output the COMPLETE file only. Blank lines must be completely empty (no spaces). No explanations, no placeholders, no TODOs.
