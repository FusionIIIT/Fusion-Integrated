from datetime import datetime, timedelta

DECISION_PERIOD_HOURS = 12

def validate_lead_time(submitted_on, requested_for):
    return submitted_on <= (requested_for - timedelta(hours=DECISION_PERIOD_HOURS))

def is_decision_expired(submitted_at, now, hours=DECISION_PERIOD_HOURS):
    return now >= (submitted_at + timedelta(hours=hours))
