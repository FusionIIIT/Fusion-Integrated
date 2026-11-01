"""
What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "id": "fts", "name": "File Tracking System", "url": "/fts/",
}

NAV_ITEMS = [
    # Add any necessary nav items here
]

#: Every permission this module recognises; ROLE_GRANTS below says who holds each.
PERMISSIONS = []

#: Performed by a service or a scheduled task, so no designation holds them.
SYSTEM_PERMISSIONS = []

#: Keyed by the designation name as it exists in globals_designation.
ROLE_GRANTS = {}
