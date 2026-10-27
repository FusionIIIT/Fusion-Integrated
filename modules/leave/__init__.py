# Employee Leave Management Module

"""Leave categories and entitlements."""
LEAVE_CATEGORIES = {
    "CL": "Casual Leave",
    "RH": "Restricted Holiday",
    "SCL": "Special Casual Leave",
    "EL": "Earned Leave",
    "COL": "Commuted Leave",
    "VL": "Vacation Leave",
}

# Entitlements per year
ENTITLEMENTS = {
    "CL": 8,  # Casual Leave - 8 days/year
    "RH": 2,  # Restricted Holiday - 2 days/year
    "SCL": 15,  # Special Casual Leave - up to 15 days/year
    "EL": "carry-forward",  # Earned Leave - carries forward
    "COL": "carry-forward",  # Commuted Leave - carries forward
    "VL": "carry-forward",  # Vacation Leave - carries forward
}

# Leave status values
LEAVE_STATUS = {
    "draft": "Draft",
    "pending": "Pending",
    "approved": "Approved",
    "cancelled": "Cancelled",
    "resumed": "Resumed",
}

# Leave request types
REQUEST_TYPES = {
    "initial": "Initial Request",
    "extension": "Extension Request",
    "resumption": "Resumption Request",
}
