import { useState } from "react";
import { Button, Container, Group, TextInput } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { notifyDone, notifyError } from "../components/notify";
import { useScheduleSeminar, useSeminarRequests } from "../api/hooks";
import type { SeminarRequest } from "../api/types";

export default function SeminarQueuePage() {
  const { data, error, isPending } = useSeminarRequests();
  const schedule = useScheduleSeminar();
  const [when, setWhen] = useState<Record<number, string>>({});
  const [venue, setVenue] = useState<Record<number, string>>({});

  const columns = [
    { key: "id", header: "#", render: (r: SeminarRequest) => r.id },
    { key: "status", header: "Status", render: (r: SeminarRequest) => <StatusBadge status={r.status} /> },
    {
      key: "act", header: "Schedule",
      render: (r: SeminarRequest) => r.status !== "awaiting_scheduling" ? null : (
        <Group gap="xs" wrap="nowrap">
          <TextInput size="xs" type="datetime-local" value={when[r.id] ?? ""}
            onChange={(e) => setWhen({ ...when, [r.id]: e.currentTarget.value })} />
          <TextInput size="xs" placeholder="Venue" value={venue[r.id] ?? ""}
            onChange={(e) => setVenue({ ...venue, [r.id]: e.currentTarget.value })} />
          <Button size="xs" disabled={!when[r.id] || !venue[r.id]} onClick={() => {
            const at = when[r.id];
            const place = venue[r.id];
            if (!at || !place) return;
            schedule.mutate({ id: r.id, scheduled_for: new Date(at).toISOString(), venue: place },
              { onSuccess: () => notifyDone("Seminar scheduled."), onError: notifyError });
          }}>Schedule</Button>
        </Group>
      ),
    },
  ];

  return (
    <Container size="lg" py="md">
      <PageHeader title="Seminar queue" subtitle="Schedule and log requested graduate seminars." />
      {error ? <ErrorState error={error} /> : (
        <DataTable rows={data ?? []} columns={columns} loading={isPending} minWidth={720}
          rowKey={(r) => r.id} empty={{ title: "No seminar requests are waiting." }} />
      )}
    </Container>
  );
}
