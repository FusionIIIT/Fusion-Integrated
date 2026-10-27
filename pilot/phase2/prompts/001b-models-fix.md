Review of the models.py written in task 001 found three defects. Fix only these, with SEARCH/REPLACE edits:

1. Both `category = models.CharField(max_length=2, ...)` fields (in LeaveApplication and in LeaveBalance) must use max_length=3: "SCL" and "COL" are three characters and would be rejected by the database.
2. LeaveApplication.kind must have default=RequestKind.LEAVE (most requests are leave requests; DESIGN.md).
3. LeaveAction.Meta.ordering must be ["created_at"] (history reads oldest first; DESIGN.md).

Do not change anything else.
