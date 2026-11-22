from modules.quiz.machines.quiz_machine import STUDENT, SYSTEM
from modules.quiz.state_machine import GuardFailed, Machine, Transition


def _start(ctx):
    if not ctx.get("eligible"):
        raise GuardFailed("INELIGIBLE")
    if ctx.get("attempts_used", 0) >= ctx.get("max_attempts", 0):
        raise GuardFailed("ATTEMPTS_EXHAUSTED")
    if ctx.get("has_active_attempt"):
        raise GuardFailed("ACTIVE_ATTEMPT_EXISTS")
    if ctx["now"] < ctx.get("quiz_start_at", ctx["now"]):
        raise GuardFailed("NOT_AVAILABLE")


def _submit(ctx):
    if not ctx.get("confirm"):
        raise GuardFailed("CONFIRM_REQUIRED")
    if ctx["now"] > ctx["deadline_at"]:
        raise GuardFailed("DEADLINE_PASSED")
    if not ctx.get("allow_unanswered", True) and ctx.get("unanswered", 0):
        raise GuardFailed("UNANSWERED_NOT_ALLOWED")


M2 = Machine(
    "attempt",
    (
        Transition((None,), "start", (STUDENT,), _start, "STARTED"),
        Transition(("STARTED",), "submit", (STUDENT,), _submit, "SUBMITTED"),
        Transition(
            ("STARTED",),
            "auto_submit",
            (SYSTEM,),
            lambda c: c["now"] >= c["deadline_at"],
            "SUBMITTED",
        ),
        Transition(("STARTED",), "tab_violation", (STUDENT,), lambda c: True, "STARTED"),
    ),
)
