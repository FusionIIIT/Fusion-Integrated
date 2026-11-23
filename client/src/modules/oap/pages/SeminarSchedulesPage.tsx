import { Container } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSeminarSchedules } from "../api/hooks";
import type { SeminarSchedule } from "../api/types";

const columns = [
  { key: "when", header: "When", render: (r: SeminarSchedule) => new Date(r.scheduled_for).toLocaleString() },
  { key: "venue", header: "Venue", render: (r: SeminarSchedule) => r.venue },
];

export default function SeminarSchedulesPage() {
  const { data, error, isPending } = useSeminarSchedules();
  return (
    <Container size="lg" py="md">
      <PageHeader title="Seminar schedules" subtitle="Scheduled graduate seminars." />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={480}
          rowKey={(r) => r.id} empty={{ title: "No seminars are scheduled yet." }} />
      )}
    </Container>
  );
}
