import { Button, Card, Container } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useBackups, useTriggerManualBackup } from "../api/hooks";
import type { BackupRecord } from "../api/types";

function PlayIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}

export default function BackupsPage() {
  const { data, isPending, error } = useBackups();
  const triggerMutation = useTriggerManualBackup();
  const { can } = useAuth();

  const canManage = can("badms.backup.manage");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleManualBackup = () => {
    triggerMutation.mutate("fusion_integrated", {
      onSuccess: () => {
        notifications.show({ title: "Backup Triggered", message: "Manual backup executed successfully." });
      },
      onError: (err) => {
        notifications.show({ title: "Backup Failed", message: err.message, color: "red" });
      },
    });
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Database Backups"
        subtitle="Manage point-in-time database dumps and automated backup status"
        action={
          canManage && (
            <Button
              leftSection={<PlayIcon />}
              onClick={handleManualBackup}
              loading={triggerMutation.isPending}
            >
              Trigger Manual Backup
            </Button>
          )
        }
      />
      <Card padding="lg">
        <DataTable<BackupRecord>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          empty={{ title: "No backup records found", description: "No backups have been created or logged yet." }}
          columns={[
            { key: "id", header: "ID", render: (r) => r.id },
            { key: "dataset_name", header: "Dataset", render: (r) => r.dataset_name },
            { key: "backup_type", header: "Type", render: (r) => r.backup_type },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "checksum",
              header: "Checksum",
              render: (r) => (r.checksum_sha256 ? `${r.checksum_sha256.substring(0, 12)}...` : "—"),
            },
            {
              key: "created_at",
              header: "Created",
              render: (r) => new Date(r.created_at).toLocaleString(),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
