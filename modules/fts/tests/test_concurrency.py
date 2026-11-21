"""Concurrency and transactional integrity tests for FTS."""
import pytest
from django.db import transaction

from modules.fts.models.files import File
from modules.fts.services.files import create_file
from modules.fts.services.movements import forward_file

pytestmark = pytest.mark.django_db


def test_sequential_movements_maintain_strict_sequence_order():
    file_obj = create_file(
        subject="Concurrent Testing File",
        comment_text="Initial creation comment.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="staff_202",
        recipient_role="Junior Superintendent",
    )

    with transaction.atomic():
        locked_file = File.objects.select_for_update().get(id=file_obj.id)
        assert locked_file.status == "CIRCULATED"

        mov1 = forward_file(
            file_id=locked_file.id,
            actor_user_id=202,
            actor_username="staff_202",
            actor_role="Junior Superintendent",
            to_user_id=303,
            to_username="dean_303",
            to_role="Dean Academic",
            comment_text="First sequential forward.",
        )
        assert mov1.sequence == 2

    mov2 = forward_file(
        file_id=file_obj.id,
        actor_user_id=303,
        actor_username="dean_303",
        actor_role="Dean Academic",
        to_user_id=404,
        to_username="dir_404",
        to_role="Director",
        comment_text="Second forward.",
    )
    assert mov2.sequence == 3
