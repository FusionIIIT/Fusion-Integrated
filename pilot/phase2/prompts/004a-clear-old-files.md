Task 004 failed: lifecycle.py still holds 707 lines of Phase-1 code, the model started copying it, and the response hit the output token limit before the new file was written. views.py (436 lines) and serializers.py (186 lines) would fail the same way. They are all being rewritten from scratch in the next tasks, so first empty them.

Replace the whole content of each of the three files with exactly one line, and nothing else:

modules/leave/services/lifecycle.py:
"""Leave decision and cancellation services (rewritten in Phase 2)."""

modules/leave/api/views.py:
"""Leave API views (rewritten in Phase 2)."""

modules/leave/api/serializers.py:
"""Leave API serializers (rewritten in Phase 2)."""

Do not output anything else. Do not ask for more files.
