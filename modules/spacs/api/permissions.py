"""Permission gates for the SPACS API.

Enforces:
- HasModuleGrant("spacs") on every endpoint
- Granular HasPermission checks matching registry.py declarations
"""
from __future__ import annotations

from fusion_auth.permissions import HasModuleGrant, HasPermission

MODULE_GRANT = HasModuleGrant("spacs")

# Shortcut helper functions for SPACS permission classes
def require_spacs_permission(*codes: str):
    return [MODULE_GRANT, HasPermission(*codes)]
