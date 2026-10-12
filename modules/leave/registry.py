"""What the server tells the shell about this module (ADR-0010).

Skeleton only: the module says where it lives, but declares no screens, nav
items or permissions yet. `status="planned"` keeps it invisible and unroutable
until the features land — see docs/03-platform/module-authoring-guide.md.
"""
MODULE = {
    "code": "leave",
    "label": "Leave",
    "base_path": "/leave",
    "status": "planned",
}

NAV_ITEMS = []

#: Declared once the features exist. A permission with no holder and no screen
#: is exactly what the manifest check refuses, so these stay empty for now.
PERMISSIONS = []

SYSTEM_PERMISSIONS = []
