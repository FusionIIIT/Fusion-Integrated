import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Grid,
  Select,
  Stack,
  Text,
} from "@mantine/core";


import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useMyLeaves } from "../api/hooks";
import type { LeaveRequest } from "../api/types";


export default function AllLeavesPage() {

  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);

  const { data, isPending, error } = useMyLeaves({
    status: statusFilter || undefined,
    category: categoryFilter || undefined,
  });

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const rows = (data?.results ?? []) as LeaveRequest[];

  return (
    <Container size="xl">
      <PageHeader
        title="All Leaves"
        subtitle="Institute-wide leave monitoring and administration"
      />

      <Card padding="md" withBorder radius="md" mb="md">
        <Grid>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <Select
              label="Filter by Category"
              placeholder="All categories"
              clearable
              data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
              value={categoryFilter}
              onChange={setCategoryFilter}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <Select
              label="Filter by Status"
              placeholder="All statuses"
              clearable
              data={[
                { value: "draft", label: "Draft" },
                { value: "awaiting_substitute", label: "Awaiting Substitute" },
                { value: "awaiting_unit_head", label: "Awaiting Unit Head" },
                { value: "awaiting_sanction", label: "Awaiting Sanction" },
                { value: "approved", label: "Approved" },
                { value: "rejected", label: "Rejected" },
                { value: "withdrawn", label: "Withdrawn" },
                { value: "cancelled", label: "Cancelled" },
              ]}
              value={statusFilter}
              onChange={setStatusFilter}
            />
          </Grid.Col>
        </Grid>
      </Card>

      <Card padding="lg" withBorder radius="md">
        <DataTable<LeaveRequest>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={850}
          empty={{
            title: "No leave records found",
            description: "No leaves match the selected filters",
          }}
          columns={[
            {
              key: "id",
              header: "ID",
              render: (r) => <Text fw={600}>#{r.id}</Text>,
            },
            {
              key: "employee",
              header: "Employee",
              render: (r) => <Text size="sm">User #{r.user_id}</Text>,
            },
            {
              key: "category",
              header: "Category",
              render: (r) => (
                <Badge color="indigo" variant="light">
                  {r.category}
                </Badge>
              ),
            },
            {
              key: "dates",
              header: "Duration",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm">
                    {r.start_date} to {r.end_date}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.days_counted} day(s)
                  </Text>
                </Stack>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "submitted",
              header: "Submitted",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {r.submitted_at ? new Date(r.submitted_at).toLocaleDateString() : "-"}
                </Text>
              ),
            },
          ]}
        />
      </Card>

    </Container>
  );
}
