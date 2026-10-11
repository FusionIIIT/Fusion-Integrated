import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { errorMessage, http } from "../../../lib/http";

interface LeaveRequestItem {
  id: number;
  leave_type_code: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  total_days: string;
  status: string;
  reason: string;
}

export default function MyLeavesPage() {
  const queryClient = useQueryClient();
  const requestsQuery = useQuery({
    queryKey: ["elm", "applications"],
    queryFn: async () => (await http.get<LeaveRequestItem[]>("/elm/applications")).data,
  });

  const actionMutation = useMutation({
    mutationFn: async ({ id, action }: { id: number; action: "withdraw" | "cancel" }) => {
      return (await http.post(`/elm/applications/${id}/${action}`, {})).data;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["elm"] });
    },
  });

  const rows = requestsQuery.data ?? [];

  return (
    <Container size="lg" py="lg">
      <Stack gap="md">
        <Title order={2}>My Leaves</Title>
        {requestsQuery.isPending && <Loader size="sm" />}
        {requestsQuery.isError && <Alert color="red">{errorMessage(requestsQuery.error)}</Alert>}
        <Card withBorder>
          {rows.length === 0 ? (
            <Text c="dimmed" size="sm">No leave applications found.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Start</Table.Th>
                  <Table.Th>End</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((item) => (
                  <Table.Tr key={item.id}>
                    <Table.Td>{item.leave_type_code}</Table.Td>
                    <Table.Td>{item.start_date}</Table.Td>
                    <Table.Td>{item.end_date}</Table.Td>
                    <Table.Td>{item.total_days}</Table.Td>
                    <Table.Td>{item.reason}</Table.Td>
                    <Table.Td>
                      <Badge variant="light">{item.status}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        {item.status === "PENDING" && (
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            loading={actionMutation.isPending}
                            onClick={() => actionMutation.mutate({ id: item.id, action: "withdraw" })}
                          >
                            Withdraw
                          </Button>
                        )}
                        {item.status === "APPROVED" && (
                          <Button
                            size="xs"
                            color="orange"
                            variant="light"
                            loading={actionMutation.isPending}
                            onClick={() => actionMutation.mutate({ id: item.id, action: "cancel" })}
                          >
                            Cancel
                          </Button>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
