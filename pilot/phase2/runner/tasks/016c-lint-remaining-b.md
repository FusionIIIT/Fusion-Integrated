TITLE: Fix the remaining ruff findings in the application and lifecycle services
FORMAT: diff
EDIT: modules/leave/services/applications.py modules/leave/services/lifecycle.py
LIMIT: 900
POST: none
---
After ruff's automatic fixes, `ruff check .` still reports these findings in the services. Fix only these, with SEARCH/REPLACE edits (do not change behaviour):

1. applications.py (B904, three places): inside `except policy.PolicyError as e:` blocks, `raise LeaveError(str(e))` must chain the cause: `raise LeaveError(str(e)) from e`. This occurs once in get_balance and twice in apply_leave (eligibility and day count).
2. applications.py, apply_leave step 3 (B904): the block
    try:
        balance = get_balance(user_id, kind, category, start_date.year)
    except LeaveError as e:
        raise LeaveError(str(e))
   only re-raises the same error. Replace it with the single line
    balance = get_balance(user_id, kind, category, start_date.year)
3. applications.py, respond_to_substitute (E501): the NotFound message f-string is longer than 100 characters. Use `raise NotFound(f"Not awaiting a substitute response (status {app.status}, stage {app.stage}).")`, on one line if it fits within 100 characters, otherwise inside parentheses on its own line.
4. lifecycle.py (E501, two lines): in finalize's docstring split the line "- On CANCELLATION approval: set parent status to CANCELLED and subtract parent's days from balance." onto two lines, and shorten the comment "# Ensure parent is a LEAVE request (cancellations of cancellations are not expected per workflow)" to "# Only a LEAVE request can be cancelled; a cancellation cannot be."

Do not change anything else.
