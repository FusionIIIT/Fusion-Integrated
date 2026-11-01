"""What the server tells the shell about this module (ADR-0010).

Nav items carry `required_permission` and the server filters before sending —
the client does zero filtering, so a link a role cannot use never reaches the
browser at all.
"""
MODULE = {
    "code": "rspc", "label": "RSPC", "icon": "Flask",
    "base_path": "/rspc", "nav_section": "Research", "sort_order": 30,
    "status": "active",
}

PERMISSIONS = [
    ("rspc.proposal.submit", "Submit a research project proposal"),
    ("rspc.proposal.view_self", "View own proposals"),
    ("rspc.proposal.recommend", "Recommend a proposal from the department"),
    ("rspc.proposal.verify", "Verify a department-recommended proposal"),
    ("rspc.proposal.decide", "Decide an admin-verified proposal"),
    ("rspc.proposal.authorize", "Authorize a proposal forwarded to Director"),
    ("rspc.proposal.view_queue", "View the review queue"),
]

ROLE_GRANTS = {
    "Faculty": ["rspc.proposal.submit", "rspc.proposal.view_self"],
    "HoD": ["rspc.proposal.recommend", "rspc.proposal.view_queue"],
    "RSPC Admin": ["rspc.proposal.verify", "rspc.proposal.view_queue"],
    "Dean-RSPC": ["rspc.proposal.decide", "rspc.proposal.view_queue"],
    "Director": ["rspc.proposal.authorize", "rspc.proposal.view_queue"],
}

NAV_ITEMS = [
    {"code": "rspc.submit", "label": "Submit Proposal", "icon": "PaperPlane", "to": "/rspc/submit", "required_permission": "rspc.proposal.submit", "sort_order": 5},
    {"code": "rspc.mine", "label": "My Proposals", "icon": "UserCheck", "to": "/rspc/mine", "required_permission": "rspc.proposal.view_self", "sort_order": 10},
    {"code": "rspc.queue", "label": "Review Queue", "icon": "CalendarBlank", "to": "/rspc/queue", "required_permission": "rspc.proposal.view_queue", "sort_order": 20},
]
