import { Button, Card, Container, Group, Stack, Table, Text, Title } from "@mantine/core";
import { useApproveVisit, useRejectVisit, useVisits } from "../api/hooks";

export default function ApprovalsPage() {
  const { data: visits, isLoading } = useVisits();
  const approveVisit = useApproveVisit();
  const rejectVisit = useRejectVisit();

  const pending = visits?.filter((v) => v.status === "requested") || [];

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        <Title order={2}>Host Approvals Queue</Title>

        {isLoading && <Text>Loading approvals...</Text>}

        <Card withBorder padding="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Pass ID</Table.Th>
                <Table.Th>Visitor</Table.Th>
                <Table.Th>Purpose</Table.Th>
                <Table.Th>Requested Date</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {pending.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={5}>
                    <Text ta="center" c="dimmed">No pending visits awaiting your approval.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                pending.map((v) => (
                  <Table.Tr key={v.id}>
                    <Table.Td>{v.pass_number}</Table.Td>
                    <Table.Td>{v.visitor.first_name} {v.visitor.last_name}</Table.Td>
                    <Table.Td>{v.purpose}</Table.Td>
                    <Table.Td>{new Date(v.valid_from).toLocaleDateString()}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          loading={approveVisit.isPending}
                          onClick={() => approveVisit.mutate(v.id)}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="outline"
                          loading={rejectVisit.isPending}
                          onClick={() => rejectVisit.mutate({ visitId: v.id, reason: "Host not available" })}
                        >
                          Reject
                        </Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>
    </Container>
  );
}
