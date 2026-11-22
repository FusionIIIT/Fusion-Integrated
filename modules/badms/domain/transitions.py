"""The source workflow tables are the sole authority for valid transitions."""

ARCHIVE_TRANSITIONS = {
    "Submitted": {"hod_reject": "Rejected", "hod_approve": "HoD Approved"},
    "HoD Approved": {
        "classify_sensitive": "Classified Sensitive / Routed to IT Security",
        "classify_other": "Classified Non-Sensitive / Policy Applied",
    },
    "Classified Sensitive / Routed to IT Security": {
        "encrypt": "Sensitive Archive Encrypted",
    },
}

STORAGE_TRANSITIONS = {"Submitted": {"reject": "Rejected", "approve": "Approved"}}

RESTORE_TRANSITIONS = {
    "Sensitive Restoration Pending Approval": {
        "reject": "Rejected", "approve": "Approved for Restoration",
    },
    "Approved for Restoration": {"restore": "Restored"},
    "Restoration Requested / Standard Path": {"restore": "Restored"},
}


def next_state(transitions: dict, current: str, action: str) -> str:
    try:
        return transitions[current][action]
    except KeyError as exc:
        raise ValueError("This action is not allowed from the current state.") from exc
