import {
  Badge,
  Card,
  Container,
  Stack,
  Text,
  Title,
} from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCalendars, usePolicies } from "../api/hooks";
import type { Calendar, Policy } from "../api/types";

export default function PolicyPage() {
  const { data: policies, isPending: polPending, error: polError } = usePolicies();
  const { data: calendars, isPending: calPending, error: calError } = useCalendars();

  if (polError) return <Container size="xl"><ErrorState error={polError} /></Container>;
  if (calError) return <Container size="xl"><ErrorState error={calError} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Policy & Calendars"
        subtitle="Manage institute leave policies, rules, and academic holiday calendars"
      />

      <Stack gap="xl">
        <Card padding="lg" withBorder>
          <Title order={4} mb="md">Configured Leave Policies</Title>
          <DataTable<Policy>
            rows={policies ?? []}
            loading={polPending}
            rowKey={(r) => r.id}
            empty={{ title: "No policies configured", description: "No leave policies found." }}
            minWidth={700}
            columns={[
              {
                key: "version",
                header: "Version",
                render: (r) => <Text fw={600}>{r.version}</Text>,
              },
              {
                key: "effective",
                header: "Effective Period",
                render: (r) => (
                  <Text size="sm">
                    {r.effective_from} to {r.effective_to ?? "Ongoing"}
                  </Text>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (r) => (
                  <Badge color={r.published ? "green" : "gray"}>
                    {r.published ? "Published" : "Draft"}
                  </Badge>
                ),
              },
              {
                key: "note",
                header: "Note",
                render: (r) => <Text size="sm" c="dimmed">{r.note ?? "—"}</Text>,
              },
            ]}
          />
        </Card>

        <Card padding="lg" withBorder>
          <Title order={4} mb="md">Holiday & Vacation Calendars</Title>
          <DataTable<Calendar>
            rows={calendars ?? []}
            loading={calPending}
            rowKey={(r) => r.id}
            empty={{ title: "No calendars configured", description: "No holiday or vacation calendars found." }}
            minWidth={700}
            columns={[
              {
                key: "year",
                header: "Year",
                render: (r) => <Text fw={600}>{r.year}</Text>,
              },
              {
                key: "version",
                header: "Version",
                render: (r) => <Text size="sm">v{r.version}</Text>,
              },
              {
                key: "status",
                header: "Status",
                render: (r) => (
                  <Badge color={r.published ? "green" : "gray"}>
                    {r.published ? "Published" : "Draft"}
                  </Badge>
                ),
              },
            ]}
          />
        </Card>
      </Stack>
    </Container>
  );
}
