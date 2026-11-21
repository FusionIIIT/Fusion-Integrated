from enum import StrEnum


class StockStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ISSUED = "issued"


class FeedbackStatus(StrEnum):
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    CLOSED = "closed"


class DetailChangeStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


STOCK_TRANSITIONS = {
    ("pending", "approved"),
    ("pending", "rejected"),
    ("approved", "issued"),
    ("approved", "rejected"),
}
FEEDBACK_TRANSITIONS = {
    ("submitted", "reviewed"),
    ("submitted", "closed"),
    ("reviewed", "resolved"),
    ("reviewed", "closed"),
    ("resolved", "closed"),
}
DETAIL_TRANSITIONS = {("pending", "approved"), ("pending", "rejected")}


def validate_stock_transition(frm, to):
    if (frm, to) not in STOCK_TRANSITIONS:
        raise ValueError(f"invalid stock transition {frm}->{to}")


def validate_feedback_transition(frm, to):
    if (frm, to) not in FEEDBACK_TRANSITIONS:
        raise ValueError(f"invalid feedback transition {frm}->{to}")


def validate_detail_transition(frm, to):
    if (frm, to) not in DETAIL_TRANSITIONS:
        raise ValueError(f"invalid detail transition {frm}->{to}")
