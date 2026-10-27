# Task: fix remaining problems in modules/leave/models.py (output the COMPLETE file; change nothing else)

`manage.py check` reports:
  leave_management.LeaveApplication.resumption_status: (fields.E009) 'max_length' is too small to fit the longest value in 'choices' (22 characters).
Fix: set `max_length=30` on `resumption_status`.

`ruff check` reports W293 "Blank line contains whitespace" on several blank lines (for example lines 158, 160, 163, 180) and other
whitespace/line-length findings. Every blank line in the output file must be completely empty (zero spaces or tabs), and every line must be at most 100 characters.
Do not change any field, choice, constraint or index otherwise. No explanations, no placeholders, no TODOs.
