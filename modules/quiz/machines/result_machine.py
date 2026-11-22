from modules.quiz.machines.quiz_machine import PROFESSOR, STUDENT, SYSTEM
from modules.quiz.state_machine import Machine, Transition


def _final_state(ctx):
    return (
        "EVALUATED"
        if all(item.get("final", item.get("kind") == "objective") for item in ctx["responses"])
        else ctx.get("state", "PARTIALLY_EVALUATED")
    )


M3 = Machine(
    "result",
    (
        Transition(
            ("NOT_EVALUATED", "PARTIALLY_EVALUATED"), "auto_evaluate", (SYSTEM,), None, "EVALUATED"
        ),
        Transition(
            ("PARTIALLY_EVALUATED",), "finalize_subjective", (PROFESSOR,), None, _final_state
        ),
        Transition(
            ("EVALUATED",),
            "release",
            (PROFESSOR,),
            lambda c: c.get("owns_course", False),
            "RELEASED",
        ),
        Transition(
            ("RELEASED",),
            "view_result",
            (STUDENT,),
            lambda c: c.get("visibility_permits", False),
            "RELEASED",
        ),
    ),
)
