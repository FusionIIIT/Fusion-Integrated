import os
import shutil
import tempfile
import uuid
import threading
from pathlib import Path
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.db import connections
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import BackupRecord, BackupSchedule, RestoreRecord, HealthCheck
from ..views import backups as backup_views
from ..views.backups import MAIN_DB_ALIAS, RESTORABLE_DB_NAMES

class ConsoleAPITestCase(APITestCase):
    """Base for the operator console endpoints.

    Every view here is @permission_classes([IsAuthenticated]), so a client that
    does not sign in gets 401 and never reaches the code under test.
    """

    # Both aliases: SystemDBRouter puts auth/sessions and the backup
    # bookkeeping tables in system_db.
    databases = {"default", "system_db"}

    def setUp(self):
        super().setUp()
        # is_staff, because the destructive endpoints (delete a backup,
        # restore over the ERP, delete a schedule) are IsAdminUser.
        self.operator = User.objects.create_user(
            username="operator", email="operator@test.invalid",
            password="console-test-password", is_staff=True)
        self.client.force_authenticate(user=self.operator)
        # The views resolve db_name back to a settings alias and reject
        # anything unconfigured, so read the real name rather than invent one.
        self.db_name = connections[MAIN_DB_ALIAS].settings_dict["NAME"]


# Mocking subprocess for backup/restore commands
class BackupRestoreTests(ConsoleAPITestCase):

    def setUp(self):
        super().setUp()
        # Create a temporary directory for backups during tests
        self.test_backup_dir = tempfile.mkdtemp()
        self.patcher_backup_dir = patch('api.views.backups.BACKUP_DIR', new=Path(self.test_backup_dir))
        self.mock_backup_dir = self.patcher_backup_dir.start()
        
        # Patch _get_db_config to return dummy Postgres config
        self.patcher_db_config = patch('api.views.backups._get_db_config')
        self.mock_db_config = self.patcher_db_config.start()
        self.mock_db_config.return_value = {
            "name": "test_db",
            "user": "test_user",
            "password": "test_password",
            "host": "localhost",
            "port": "5432",
        }
        
        # Patches for subprocess and threading to avoid actual execution
        self.patcher_subprocess = patch('subprocess.run')
        self.mock_subprocess = self.patcher_subprocess.start()
        self.mock_subprocess.return_value.returncode = 0
        self.mock_subprocess.return_value.stderr = ""
        
        self.patcher_thread = patch('threading.Thread')
        self.mock_thread = self.patcher_thread.start()
        
        # Setup run_backup/run_restore execution immediately instead of threading
        def side_effect_run_backup(*thread_args, **thread_kwargs):
             target = thread_kwargs.get('target')
             target_args = thread_kwargs.get('args', ())

             if target is None and thread_args:
                 target = thread_args[0]
             if 'args' not in thread_kwargs and len(thread_args) > 1:
                 target_args = thread_args[1]

             mock_thread_instance = MagicMock()
             mock_thread_instance.start.side_effect = lambda: target(*target_args)
             return mock_thread_instance
        self.mock_thread.side_effect = side_effect_run_backup

    def tearDown(self):
        self.patcher_backup_dir.stop()
        self.patcher_subprocess.stop()
        self.patcher_thread.stop()
        self.patcher_db_config.stop()
        shutil.rmtree(self.test_backup_dir)

    def test_sync_orphaned_backups(self):
        # Create a dummy dump file in the backup directory
        # The file name should be a valid UUID
        fake_uuid = uuid.uuid4()
        dump_path = os.path.join(self.test_backup_dir, f"{fake_uuid}.dump")
        with open(dump_path, 'w') as f:
            f.write("orphan")
        
        # Ensure no record exists yet
        self.assertFalse(BackupRecord.objects.filter(id=fake_uuid).exists())
        
        # Calling list-backups triggers the sync
        url = reverse('list-backups')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if the record was created
        self.assertTrue(BackupRecord.objects.filter(id=fake_uuid).exists())
        record = BackupRecord.objects.get(id=fake_uuid)
        self.assertEqual(record.status, 'success')

    def test_list_backups_empty(self):
        url = reverse('list-backups')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_create_backup_success(self):
        url = reverse('create-backup')
        data = {'db_name': self.db_name}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BackupRecord.objects.count(), 1)
        record = BackupRecord.objects.first()
        self.assertEqual(record.db_name, self.db_name)
        self.assertEqual(record.status, 'success', record.error_message) # Because subprocess mock returns success

    def test_delete_backup(self):
        # Create a dummy backup record and file
        record = BackupRecord.objects.create(
            db_name='test_db',
            status='success',
            file_path=os.path.join(self.test_backup_dir, f"{uuid.uuid4()}.dump")
        )
        # Create the actual file
        with open(record.file_path, 'w') as f:
            f.write("dummy dump content")

        url = reverse('delete-backup', args=[record.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BackupRecord.objects.count(), 0)
        self.assertFalse(os.path.exists(record.file_path))

    def test_get_backup(self):
        record = BackupRecord.objects.create(
            db_name='test_db',
            status='success'
        )
        url = reverse('get-backup', args=[record.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(record.id))

    def test_restore_backup_success(self):
        # Need an existing successful backup
        # Restore is limited to the real ERP databases by RESTORABLE_DB_NAMES,
        # so the record has to name one — a test-database name is refused, and
        # rightly so.
        backup_record = BackupRecord.objects.create(
            db_name=sorted(RESTORABLE_DB_NAMES)[0],
            status='success',
            file_path=os.path.join(self.test_backup_dir, f"{uuid.uuid4()}.dump")
        )
         # Create the file
        with open(backup_record.file_path, 'w') as f:
            f.write("dummy dump content")

        url = reverse('restore-backup', args=[backup_record.id])
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RestoreRecord.objects.count(), 1)
        restore = RestoreRecord.objects.first()
        self.assertEqual(restore.status, 'success')
        self.assertEqual(restore.source_backup, backup_record)

    def test_restore_backup_not_found(self):
        url = reverse('restore-backup', args=[uuid.uuid4()])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_restores(self):
        RestoreRecord.objects.create(db_name='test_db', status='success')
        url = reverse('list-restores')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class ScheduleTests(ConsoleAPITestCase):

    def setUp(self):
        super().setUp()
        # We need to mock the scheduler to avoid actual job scheduling
        self.patcher_scheduler = patch('api.scheduler.get_scheduler')
        self.mock_scheduler_func = self.patcher_scheduler.start()
        self.mock_scheduler = MagicMock()
        self.mock_scheduler_func.return_value = self.mock_scheduler
        self.mock_scheduler.running = True
        
        # Configure job mock for next_run_time to avoid Django trying to save a MagicMock to DB
        mock_job = MagicMock()
        mock_job.next_run_time = timezone.now() + timedelta(days=1)
        self.mock_scheduler.get_job.return_value = mock_job
        self.mock_scheduler.add_job.return_value = mock_job

    def tearDown(self):
        self.patcher_scheduler.stop()

    def test_create_schedule_daily(self):
        url = reverse('save-schedule')
        data = {
            'db_name': 'test_db',
            'frequency': 'daily',
            'hour': 3,
            'minute': 30,
            'enabled': True
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BackupSchedule.objects.count(), 1)
        schedule = BackupSchedule.objects.first()
        self.assertEqual(schedule.frequency, 'daily')
        self.assertEqual(schedule.hour, 3)
        
        # Verify scheduler.add_job was called
        self.mock_scheduler.add_job.assert_called_once()

    def test_list_schedules(self):
        BackupSchedule.objects.create(db_name='test_db')
        url = reverse('list-schedules')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_toggle_schedule(self):
        schedule = BackupSchedule.objects.create(db_name='test_db', enabled=True)
        url = reverse('toggle-schedule', args=[schedule.id])
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        schedule.refresh_from_db()
        self.assertFalse(schedule.enabled)
        
    def test_delete_schedule(self):
        schedule = BackupSchedule.objects.create(db_name='test_db')
        url = reverse('delete-schedule', args=[schedule.id])
        
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BackupSchedule.objects.count(), 0)
        
        self.mock_scheduler.remove_job.assert_called()

    def test_preview_schedule(self):
        url = reverse('preview-next-runs')
        data = {
            'frequency': 'daily',
            'hour': 10,
            'minute': 0
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('next_runs', response.data)
        self.assertEqual(len(response.data['next_runs']), 5)


class HealthCheckTests(ConsoleAPITestCase):

    def setUp(self):
        super().setUp()
        self.patcher_db_config = patch('api.views.backups._get_db_config')
        self.mock_db_config = self.patcher_db_config.start()
        self.mock_db_config.return_value = {
            "name": "test_db",
            "user": "test_user",
            "password": "test_password",
            "host": "localhost",
            "port": "5432",
        }

    def tearDown(self):
        self.patcher_db_config.stop()

    def test_run_health_check(self):
        url = reverse('run-health-check')
        data = {'db_name': 'test_db'}
        
        # We don't need to mock cursor because we are using SQLite which supports SELECT 1
        response = self.client.post(url, data, format='json')
            
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(HealthCheck.objects.count(), 1)
        self.assertEqual(HealthCheck.objects.first().status, 'success')

    def test_list_health_checks(self):
        HealthCheck.objects.create(db_name='test_db', status='success')
        url = reverse('list-health-checks')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class DestructiveEndpointPermissionTests(APITestCase):
    """The destructive endpoints are IsAdminUser, not merely IsAuthenticated.

    Every other test here signs in as staff, which satisfies that gate without
    ever proving it exists. This is the counterpart: a signed-in operator who
    is not staff must be refused.
    """

    databases = {"default", "system_db"}

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="not-an-admin", email="plain@test.invalid",
            password="console-test-password", is_staff=False)
        self.client.force_authenticate(user=self.user)

    def test_deleting_a_backup_is_refused(self):
        record = BackupRecord.objects.create(db_name="fusionlab", status="success")
        response = self.client.delete(reverse('delete-backup', args=[record.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(BackupRecord.objects.filter(id=record.id).exists())

    def test_restoring_over_the_erp_is_refused(self):
        record = BackupRecord.objects.create(db_name="fusionlab", status="success")
        response = self.client.post(reverse('restore-backup', args=[record.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(RestoreRecord.objects.count(), 0)

    def test_deleting_a_schedule_is_refused(self):
        schedule = BackupSchedule.objects.create(db_name="fusionlab", frequency="daily")
        response = self.client.delete(reverse('delete-schedule', args=[schedule.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(BackupSchedule.objects.filter(id=schedule.id).exists())
