STOCK_TRANSITIONS = {
    ("pending", "approve", "hod"): "approved",
    ("pending", "reject", "hod"): "rejected",
    ("approved", "issue", "admin"): "issued",
}

FEEDBACK_TRANSITIONS = {
    ("new", "review", "admin"): "reviewed",
    ("reviewed", "close", "admin"): "closed",
    ("reviewed", "close", "hod"): "closed",
    ("reviewed", "resolve", "admin"): "resolved",
    ("reviewed", "resolve", "hod"): "resolved",
}

OFFICIAL_TRANSITIONS = {
    ("pending", "approve", "hod"): "approved",
    ("pending", "reject", "hod"): "rejected",
}
