from modules.quiz.state_machine import GuardFailed, Machine, Transition

PROFESSOR, STUDENT, SYSTEM = "PROFESSOR", "STUDENT", "SYSTEM"


def _true(ctx):
    return True


def _publishable(ctx):
    if not ctx.get("owns_course", False):
        raise GuardFailed("NOT_COURSE_OWNER")
    if not ctx.get("questions_valid", False):
        raise GuardFailed("QUESTIONS_INVALID")
    if not ctx.get("config_valid", False):
        raise GuardFailed("CONFIG_INVALID")


def _published_state(ctx):
    return "SCHEDULED" if ctx.get("start_at") and ctx["start_at"] > ctx["now"] else "AVAILABLE"


M1 = Machine(
    "quiz",
    (
        Transition(("DRAFT",), "configure", (PROFESSOR,), _true, "DRAFT_CONFIGURED"),
        Transition(("DRAFT_CONFIGURED",), "prepare", (PROFESSOR,), _true, "READY_TO_PUBLISH"),
        Transition(("READY_TO_PUBLISH",), "publish", (PROFESSOR,), _publishable, _published_state),
        Transition(
            ("SCHEDULED",),
            "boundary_start",
            (SYSTEM,),
            lambda c: c["now"] >= c["start_at"],
            "AVAILABLE",
        ),
        Transition(
            ("AVAILABLE",),
            "boundary_close",
            (SYSTEM,),
            lambda c: c["now"] >= c["close_at"],
            "CLOSED",
        ),
        Transition(
            ("CLOSED",),
            "archive",
            (PROFESSOR,),
            lambda c: c.get("archive_permitted", False),
            "ARCHIVED",
        ),
        Transition(
            ("DRAFT", "DRAFT_CONFIGURED", "READY_TO_PUBLISH"),
            "edit",
            (PROFESSOR,),
            _true,
            lambda c: c.get("state", "DRAFT"),
        ),
    ),
)
