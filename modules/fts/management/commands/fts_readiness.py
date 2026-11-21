"""FTS module readiness check management command."""
from django.core.management.base import BaseCommand

from modules.fts.models import FileAttachment, FileComment, FileMovement, FTSFile


class Command(BaseCommand):
    help = "Verify FTS module readiness and database table integrity."

    def handle(self, *args, **options):
        self.stdout.write("Checking FTS module database connectivity and tables...")
        files_count = FTSFile.objects.count()
        movements_count = FileMovement.objects.count()
        comments_count = FileComment.objects.count()
        attachments_count = FileAttachment.objects.count()

        self.stdout.write(f"  FTS Files:        {files_count}")
        self.stdout.write(f"  File Movements:   {movements_count}")
        self.stdout.write(f"  File Comments:    {comments_count}")
        self.stdout.write(f"  File Attachments: {attachments_count}")
        self.stdout.write(self.style.SUCCESS("FTS is healthy and ready."))
