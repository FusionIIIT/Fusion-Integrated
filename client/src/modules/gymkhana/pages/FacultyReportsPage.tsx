import { useState } from "react";
import { Button, Card, Container, Drawer, Stack, Text } from "@mantine/core";
import { FaFileAlt } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDownload, useReports } from "../api/hooks";
import type { EventReport } from "../api/types";
import { dateTime, person } from "../components/format";
import { LoadMore } from "../components/LoadMore";
import { PageError } from "../components/PageError";
import { refused } from "../components/toasts";

export default function FacultyReportsPage() {
  const reports = useReports();
  const [open, setOpen] = useState<EventReport | null>(null);
  if (reports.error) return <PageError error={reports.error} />;

  return (
    <Container size="xl">
      <PageHeader title="Club Event Reports"
        subtitle="Reports submitted by the clubs you are Faculty Councillor of" />
      <Card padding="lg">
        <DataTable<EventReport>
          rows={reports.rows} loading={reports.loading} rowKey={(r) => r.id}
          columns={[
            { key: "event_name", header: "Event", render: (r) => <Text fw={600}>{r.event_name}</Text> },
            { key: "club_name", header: "Club" },
            { key: "event_date", header: "Held", render: (r) => dateTime(r.event_date) },
            { key: "submitted_at", header: "Submitted", render: (r) => dateTime(r.submitted_at) },
            {
              key: "action", header: "", align: "right",
              render: (r) => (
                <Button size="xs" variant="light" aria-label={`Review ${r.event_name}`}
                  onClick={() => setOpen(r)}>
                  Review
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaFileAlt, title: "No reports yet",
            description: "Reports appear here when your club submits one.",
          }}
        />
        <LoadMore list={reports} />
      </Card>
      <Drawer opened={open !== null} onClose={() => setOpen(null)} position="right"
        title={open?.event_name} closeButtonProps={{ "aria-label": "Close report" }}>
        {open && <ReportDetails report={open} />}
      </Drawer>
    </Container>
  );
}

function ReportDetails({ report }: { report: EventReport }) {
  const download = useDownload();
  return (
    <Stack gap="xs">
      <Text size="sm"><b>Club:</b> {report.club_name}</Text>
      <Text size="sm">
        <b>Student incharge:</b> {person(report.student_incharge_name, report.student_incharge_id)}
      </Text>
      <Text size="sm"><b>Held:</b> {dateTime(report.event_date)}</Text>
      <Text size="sm"><b>Submitted:</b> {dateTime(report.submitted_at)}</Text>
      {report.description && <Text size="sm">{report.description}</Text>}
      <Button
        mt="md" loading={download.isPending} disabled={!report.report_file}
        onClick={() => download.mutate(report.report_file ?? "", {
          onError: (e) => refused("Could not download the report", e),
        })}
      >
        Download report
      </Button>
    </Stack>
  );
}
