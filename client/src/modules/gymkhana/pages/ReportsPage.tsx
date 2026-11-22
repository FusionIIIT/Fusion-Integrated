import { useState } from "react";
import { Anchor, Button, Card, Container, Drawer, Loader, Stack, Text } from "@mantine/core";
import { FaFileAlt } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReport, useReports } from "../api/hooks";
import type { EventReport } from "../api/types";

/** UC-GYM-012: the assigned councillor reviews their club's event reports. */
export default function ReportsPage() {
  const { data, isPending, error } = useReports();
  const [open, setOpen] = useState<number | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Club Reports"
        subtitle="Event reports of the clubs you are faculty councillor for" />
      <Card padding="lg">
        <DataTable<EventReport>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ icon: FaFileAlt, title: "No reports to review",
            description: "Reports appear here for clubs where you are the assigned councillor." }}
          columns={[
            { key: "club", header: "Club", render: (r) => r.club_name },
            { key: "event", header: "Event", render: (r) => <Text fw={600}>{r.event_name}</Text> },
            { key: "when", header: "Held", render: (r) => new Date(r.event_at).toLocaleString() },
            { key: "action", header: "", align: "right", render: (r) => (
              <Button size="xs" variant="light" onClick={() => setOpen(r.id)}
                aria-label={`Review ${r.event_name}`}>Review</Button>) },
          ]}
        />
      </Card>
      <ReportDrawer id={open} onClose={() => setOpen(null)} />
    </Container>
  );
}

function ReportDrawer({ id, onClose }: { id: number | null; onClose: () => void }) {
  const { data, isPending, error } = useReport(id);
  return (
    <Drawer opened={id !== null} onClose={onClose} position="right" title="Event report"
      size="md">
      {error ? <ErrorState error={error} /> : isPending || !data ? <Loader size="sm" /> : (
        <Stack gap="xs">
          <Text fw={700}>{data.event_name}</Text>
          <Text size="sm">{data.club_name} · held {new Date(data.event_at).toLocaleString()}</Text>
          <Text size="sm">Student in charge: {data.student_incharge_name
            || `User ${data.student_incharge_user_id}`}</Text>
          <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{data.description}</Text>
          <Anchor href={data.report_link} target="_blank" rel="noreferrer noopener">
            Open the report file</Anchor>
        </Stack>
      )}
    </Drawer>
  );
}
