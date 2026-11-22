import { Card, Container } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useBackupSchedules } from "../api/hooks";
import type { BackupSchedule } from "../api/types";

export default function SchedulesPage() {
  const { data, isPending, error } = useBackupSchedules();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Backup Schedules"
        subtitle="Active backup configurations, cron specifications, and automated execution windows"
      />
      <Card padding="lg">
        <DataTable<BackupSchedule>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          empty={{ title: "No schedules configured", description: "No periodic backup schedules are active." }}
          columns={[
            { key: "id", header: "ID", render: (r) => r.id },
            { key: "name", header: "Schedule Name", render: (r) => r.name },
            { key: "cron_expression", header: "Cron", render: (r) => r.cron_expression },
            { key: "scope_type", header: "Scope", render: (r) => r.scope_type },
            {
              key: "is_active",
              header: "Status",
              render: (r) => <StatusBadge status={r.is_active ? "active" : "closed"} />,
            },
            {
              key: "last_run_at",
              header: "Last Run",
              render: (r) => (r.last_run_at ? new Date(r.last_run_at).toLocaleString() : "Never"),
            },
            {
              key: "next_run_at",
              header: "Next Run",
              render: (r) => (r.next_run_at ? new Date(r.next_run_at).toLocaleString() : "Pending"),
            },
          ]}
        />
      </Card>
    </Container>
  );
}
