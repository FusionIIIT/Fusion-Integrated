import {
  Alert, Badge, Button, Card, Container, Stack, Table, Text,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { FaCalendarAlt, FaInfoCircle } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyLeaveApplications } from "../api/hooks";
import type { LeaveStatus } from "../api/types";

function displayDate(value: string): string {
  return new Date(`${value}T00:00:00`).toLocaleDateString();
}

function statusColor(status: LeaveStatus): string {
  if (status === "approved") return "green";
  if (status === "rejected") return "red";
  if (status === "pending") return "orange";
  return "gray";
}

export default function MyLeavesPage() {
  const applications = useMyLeaveApplications();

  if (applications.error) {
    return <Container size="xl"><ErrorState error={applications.error} /></Container>;
  }

  const rows = applications.data?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="Your submitted leave requests and their recorded status"
        action={<Button component={Link} to="/apply_leave/apply">Apply leave</Button>}
      />
      <Alert variant="light" color="blue" icon={<FaInfoCircle />} mb="md">
        Requests submitted in this MVP remain Pending until an approval workflow is added.
        This screen does not calculate or display remaining leave balances.
      </Alert>
      <Card padding="lg" withBorder>
        {applications.isPending ? (
          <Text c="dimmed" size="sm">Loading your leave requests…</Text>
        ) : rows.length === 0 ? (
          <Stack align="center" gap="sm" py="xl">
            <FaCalendarAlt size={24} />
            <Text fw={600}>No leave requests yet</Text>
            <Text size="sm" c="dimmed" ta="center">
              When you submit a request, it will appear here with its current status.
            </Text>
            <Button component={Link} to="/apply_leave/apply">Apply for leave</Button>
          </Stack>
        ) : (
          <Table.ScrollContainer minWidth={760}>
            <Table striped highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Leave type</Table.Th>
                  <Table.Th>Period</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Submitted</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((application) => (
                  <Table.Tr key={application.id}>
                    <Table.Td>
                      <Stack gap={2}>
                        <Text fw={600} size="sm">{application.leave_type}</Text>
                        <Text c="dimmed" size="xs">{application.leave_type_label}</Text>
                      </Stack>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">
                        {displayDate(application.start_date)} – {displayDate(application.end_date)}
                      </Text>
                    </Table.Td>
                    <Table.Td>{application.days_requested}</Table.Td>
                    <Table.Td style={{ maxWidth: 280 }}>
                      <Text size="sm" lineClamp={3}>{application.reason}</Text>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="light" color={statusColor(application.status)}>
                        {application.status.replace("_", " ")}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{new Date(application.created_at).toLocaleDateString()}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Card>
    </Container>
  );
}
