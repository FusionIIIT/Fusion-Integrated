from types import SimpleNamespace

from modules.iwd import services


def actor(user_id, roles=()):
    return SimpleNamespace(user_id=user_id, roles=roles)


def complaint(*, reporter=7, engineer=12):
    return services.submit_complaint(
        actor=actor(reporter),
        title="Broken facility",
        description="A maintenance issue needs attention.",
        location="Block A",
        issue_category="civil",
        urgency="normal",
        metadata={"engineer_user_id": engineer},
    )


def assessed(*, cost=None):
    row = complaint()
    engineer = actor(12)
    services.assess(complaint=row, actor=engineer, assessment={"repair": "replace part"})
    if cost is not None:
        services.estimate(complaint=row, actor=engineer, total_cost=cost)
    return row
