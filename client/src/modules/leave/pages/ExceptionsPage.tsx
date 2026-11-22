import {
  Badge, Card, Container, SimpleGrid, Stack, Text, Title,
} from "@mantine/core";
import { FaTriangleAlert } from "react-icons/fa";

import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useExceptionOverview, useOverdueOutOfOffice,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";

/** BR-EL-032/033: the exception screen.
 *
 *  Everything here is a clock: how many reminders are due, how many escalations
 *  have fired, and who is still out of office past the end of approved leave. */
export default function ExceptionsPage() {
  const overview = useExceptionOverview();
  const overdue = useOverdueOutOfOffice();

  if (overview.isError) {
    return <Container size="lg"><ErrorState error={overview.error} /></Container>;
  }

  const stats = overview.data ?? {};
  const rows = overdue.data ?? [];

  const cards: { label: string; value: number; hint: string }[] = [
    { label: "Reminders due", value: stats.reminders_due ?? 0,
      hint: "Waiting long enough to nudge." },
    { label: "Escalations due", value: stats.escalations_due ?? 0,
      hint: "Past the escalation threshold." },
    { label: "Pending tasks", value: stats.pending_tasks ?? 0,
      hint: "Outstanding across the module." },
    { label: "Out of office overdue", value: stats.overdue_out_of_office ?? 0,
      hint: "Leave ended, no return recorded." },
  ];

  const columns: Column<LeaveRequest>[] = [
    { key: "request", header: "Request",
      render: (r) => <Text size="sm">#{r.id}</Text> },
    { key: "type", header: "Type", render: (r) => <Text size="sm">{r.category_label}</Text> },
    { key: "period", header: "Approved period",
      render: (r) => <Text size="sm">{r.start_date} → {r.end_date}</Text> },
    { key: "unit", header: "Unit", render: (r) => <Text size="sm">{r.org_unit_name || r.department || "—"}</Text> },
    {
      key: "state",
      header: "State",
      render: (r) => <Badge color="orange" variant="light" size="sm">
        Return not recorded
      </Badge>,
    },
  ];

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Exceptions"
        subtitle="Requests waiting, and leave past its end date without a return"
      />
      <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} mb="lg">
        {cards.map((c) => (
          <Card key={c.label} withBorder padding="md">
            <Text size="xs" c="dimmed" tt="uppercase">{c.label}</Text>
            <Title order={2} mt={4}>{c.value}</Title>
            <Text size="xs" c="dimmed" mt={4}>{c.hint}</Text>
          </Card>
        ))}
      </SimpleGrid>

      <Stack gap="xs">
        <Text fw={600}>Out of office with no recorded return</Text>
        {overdue.isError && <ErrorState error={overdue.error} />}
        <DataTable
          rows={rows}
          columns={columns}
          loading={overdue.isPending}
          rowKey={(r) => r.id}
          minWidth={700}
          empty={{
            icon: FaTriangleAlert,
            title: "Nobody is overdue",
            description: "Every approved leave past its end date has a return.",
          }}
        />
      </Stack>
    </Container>
  );
}