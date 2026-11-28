"""Policy selectors and authority routing resolution."""

from __future__ import annotations

import datetime

from modules.leave.models import AuthorityRule, Policy


def get_active_policy(on_date: datetime.date | None = None) -> Policy | None:
    """Returns the effective published policy for the date."""
    target_date = on_date or datetime.date.today()
    return (
        Policy.objects.filter(
            published=True,
            effective_from__lte=target_date,
        )
        .filter(models_q_to_date(target_date))
        .order_by("-effective_from")
        .first()
    )


def models_q_to_date(target_date: datetime.date):
    from django.db.models import Q

    return Q(effective_to__isnull=True) | Q(effective_to__gte=target_date)


def resolve_authority_route(
    policy: Policy,
    category: str,
    unit: str,
    designation: str,
    is_faculty: bool,
) -> AuthorityRule | None:
    """Resolves routing hierarchy step under BR-EL-019."""
    rules = AuthorityRule.objects.filter(policy=policy).order_by("-specificity")
    for r in rules:
        if r.category and r.category != category:
            continue
        if r.unit and r.unit != unit:
            continue
        if r.designation and r.designation != designation:
            continue
        if r.applies_to_faculty != is_faculty:
            continue
        return r
    # Fallback to general category rule or default
    return rules.filter(category=category).first() or rules.first()
