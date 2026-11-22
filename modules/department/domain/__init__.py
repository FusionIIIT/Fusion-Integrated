STOCK_TRANSITIONS = {
    ("pending", "approve"): "approved",
    ("pending", "reject"): "rejected",
    ("approved", "issue"): "issued",
}

FEEDBACK_TRANSITIONS = {
    ("new", "review"): "reviewed",
    ("reviewed", "close"): "closed",
    ("reviewed", "resolve"): "resolved",
}

OFFICIAL_TRANSITIONS = {
    ("pending", "approve"): "approved",
    ("pending", "reject"): "rejected",
}
