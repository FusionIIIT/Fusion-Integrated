"""Concurrency tests using real threads under transactional isolation."""

import threading

import pytest
from django.db import IntegrityError, connection

from modules.spacs.models import SpacsAwardCandidate, SpacsAwardCycle, SpacsCatalogueEntry


@pytest.mark.django_db(transaction=True)
def test_concurrent_award_candidate_uniqueness():
    """Verify that concurrent creation of same candidate in cycle enforces unique constraint."""
    scheme = SpacsCatalogueEntry.objects.create(
        scheme_code="CONC-AWARD-01",
        name="Convocation Award",
        scheme_type="award",
        status="published",
    )
    cycle = SpacsAwardCycle.objects.create(
        catalogue_entry=scheme,
        academic_cycle="2026-27",
    )
    barrier = threading.Barrier(2, timeout=10)
    candidates, failures = [], []

    def register():
        barrier.wait()
        try:
            c = SpacsAwardCandidate.objects.create(
                award_cycle=cycle,
                student_user_id=888,
                cpi=9.5,
            )
            candidates.append(c.id)
        except IntegrityError as exc:
            failures.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=register) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert len(candidates) == 1
    assert len(failures) == 1
    assert SpacsAwardCandidate.objects.filter(award_cycle=cycle, student_user_id=888).count() == 1
