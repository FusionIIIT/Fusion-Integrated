from datetime import date

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_legacy_booking_owner_survives_iam_reference_migration(request):
    if request.config.getoption("nomigrations", default=False):
        pytest.skip("Migration execution is enabled in the PostgreSQL CI job.")
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    old_target = [("visitor_hostel", "0001_initial")]
    try:
        executor.migrate(old_target)
        apps = executor.loader.project_state(old_target).apps
        user = apps.get_model("auth", "User").objects.create(username="legacy-owner")
        old = apps.get_model("visitor_hostel", "BookingRequest").objects.create(
            indenter_id=user.pk,
            visitor_name="Legacy guest",
            visitor_category="A",
            purpose="Visit",
            check_in_date=date(2026, 12, 1),
            check_out_date=date(2026, 12, 3),
        )
        owner_id, booking_id = user.pk, old.pk
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        migrated = (
            executor.loader.project_state(latest)
            .apps.get_model("visitor_hostel", "BookingRequest")
            .objects.get(pk=booking_id)
        )
        assert migrated.legacy_indenter_id == owner_id
        assert migrated.indenter_id is None
        assert migrated.visitor_name == "Legacy guest"
    finally:
        MigrationExecutor(connection).migrate(latest)
