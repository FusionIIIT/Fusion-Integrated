"""Store the SHA-256 of a session token instead of the token.

Live sessions survive: the cookie carries `K`, the column becomes `sha256(K)`,
and the lookup hashes before comparing. Python rather than a Postgres-only
`encode(sha256(...))`, because the suite runs on SQLite.
"""
import hashlib

from django.db import migrations, models


def hash_existing_keys(apps, schema_editor):
    """Rewrite each key in place. Not the ORM — `key` is the primary key, so
    a save() would insert a second row and reset the auto_now timestamps."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT key FROM iam_token")
        keys = [row[0] for row in cursor.fetchall()]
        for key in keys:
            cursor.execute(
                "UPDATE iam_token SET key = %s WHERE key = %s",
                [hashlib.sha256(key.encode()).hexdigest(), key])


def drop_sessions(apps, schema_editor):
    """A digest cannot be undone, so rolling back means signing in again."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DELETE FROM iam_token")


class Migration(migrations.Migration):

    dependencies = [
        ("iam", "0004_syncrun_academics_written_iamuseracademic"),
    ]

    operations = [
        # 48 held 24 bytes of hex; a sha256 hexdigest needs 64.
        migrations.AlterField(
            model_name="iamtoken",
            name="key",
            field=models.CharField(max_length=64, primary_key=True,
                                   serialize=False),
        ),
        migrations.RunPython(hash_existing_keys, drop_sessions),
    ]
