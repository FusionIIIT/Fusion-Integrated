"""Concurrency and transactional integrity tests with real threads under transaction=True.

Validates BR-FTS-001, BR-FTS-003, CFR-FTS-02.
"""
from __future__ import annotations

import threading

import pytest
from django.db import connection

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.fts.models.files import File
from modules.fts.models.movements import FileMovement
from modules.fts.services.files import create_file
from modules.fts.services.movements import forward_file

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_forwarding_race_condition_prevented_by_row_lock():
    """BR-FTS-001 & BR-FTS-003: Concurrent forwarding attempts on same file by threads.

    Uses threading.Barrier to synchronize two simultaneous forwarding attempts.
    Proves that row-level select_for_update locks prevent split custody.
    """
    file_obj = create_file(
        subject="High Concurrency Research Grant File",
        comment_text="Initial note for concurrent forward test.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="dean_202",
        recipient_role="Dean R&D",
    )

    barrier = threading.Barrier(2)
    results: list[FileMovement] = []
    errors: list[Exception] = []

    def _worker(target_id: int, target_name: str) -> None:
        try:
            barrier.wait(timeout=5)
            movement = forward_file(
                file_id=file_obj.id,
                actor_user_id=202,
                actor_username="dean_202",
                actor_role="Dean R&D",
                to_user_id=target_id,
                to_username=target_name,
                to_role="Associate Professor",
                comment_text=f"Concurrent forward to {target_name}",
            )
            results.append(movement)
        except (ConflictError, PermissionDeniedError) as e:
            errors.append(e)
        finally:
            connection.close()

    t1 = threading.Thread(target=_worker, args=(301, "reviewer_1"))
    t2 = threading.Thread(target=_worker, args=(302, "reviewer_2"))

    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    # Exactly one thread acquires the lock and succeeds; the other is rejected
    assert len(results) == 1, f"Expected 1 success, got {len(results)}"
    assert len(errors) == 1, f"Expected 1 failure, got {len(errors)}"
    assert isinstance(errors[0], (PermissionDeniedError, ConflictError))

    # Verify that file has exactly one unique holder in the database
    updated_file = File.objects.get(id=file_obj.id)
    assert updated_file.current_holder_user_id in (301, 302)
    assert FileMovement.objects.filter(file=file_obj, sequence=2).count() == 1
