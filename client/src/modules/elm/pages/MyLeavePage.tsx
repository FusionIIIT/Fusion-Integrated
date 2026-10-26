import { useQuery } from "@tanstack/react-query";
import { Alert, Badge, Container, Loader, Paper, Table, Text } from "@mantine/core";

import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type LeaveRequest = {
  id: number;
  leave_type_code: string;
  requested_start_date: string;
  requested_end_date: string;
  total_days: string;
  status: string;
  submitted_at: string;
};

export default function MyLeavePage() {
  const query = useQuery({
    queryKey: ["elm", "requests"],
    queryFn: async () => (await http.get<{ results: LeaveRequest[] }>("/leave/requests")).data.results,
  });
  const rows = query.data ?? [];

  return (
    <Container size="xl">
      <PageHeader title="My leave requests" subtitle="Track the status and dates of your requests" />
      {query.isPending && <Loader />}
      {query.error && <Alert color="red" title="Could not load requests">{errorMessage(query.error)}</Alert>}
      {!query.isPending && !query.error && rows.length === 0 && (
        <Paper withBorder p="lg"><Text>You have not submitted a leave request yet.</Text></Paper>
      )}
      {rows.length > 0 && (
        <Table.ScrollContainer minWidth={720}>
          <Table striped highlightOnHover>
            <Table.Thead><Table.Tr>
              <Table.Th>Type</Table.Th><Table.Th>Dates</Table.Th><Table.Th>Days</Table.Th><Table.Th>Status</Table.Th><Table.Th>Submitted</Table.Th>
            </Table.Tr></Table.Thead>
            <Table.Tbody>{rows.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td>{row.leave_type_code}</Table.Td>
                <Table.Td>{row.requested_start_date} – {row.requested_end_date}</Table.Td>
                <Table.Td>{row.total_days}</Table.Td>
                <Table.Td><Badge variant="light">{row.status.replaceAll("_", " ")}</Badge></Table.Td>
                <Table.Td>{new Date(row.submitted_at).toLocaleDateString()}</Table.Td>
              </Table.Tr>
            ))}</Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      )}
    </Container>
  );
}
