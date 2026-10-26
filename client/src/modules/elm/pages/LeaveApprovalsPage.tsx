import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { errorMessage, http } from "../../../lib/http";

interface PendingRequestItem {
  id: number;
  employee_id: number;
  leave_type_code: string;
  start_date: string;
  end_date: string;
  total_days: string;
  reason: string;
}

export default function LeaveApprovalsPage() {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");

  const approvalsQuery = useQuery({
    queryKey: ["elm", "approvals"],
    queryFn: async () => (await http.get<PendingRequestItem[]>("/elm/approvals")).data,
  });

  const decideMutation = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: "APPROVE" | "REJECT" }) => {
      return (
        await http.post(`/elm/applications/${id}/decide`, {
          decision,
          review_comment: comment,
        })
      ).data;
    },
    onSuccess: async () => {
      setComment("");
      await queryClient.invalidateQueries({ queryKey: ["elm"] });
    },
  });

  const rows = approvalsQuery.data ?? [];

  return (
    <Container size="lg" py="lg">
      <Stack gap="md">
        <Title order={2}>Leave Approvals</Title>
        {approvalsQuery.isPending && <Loader size="sm" />}
        {approvalsQuery.isError && <Alert color="red">{errorMessage(approvalsQuery.error)}</Alert>}
        <TextInput
          label="Reviewer Comment (optional)"
          value={comment}
          onChange={(e) => setComment(e.currentTarget.value)}
        />
        <Card withBorder>
          {rows.length === 0 ? (
            <Text c="dimmed" size="sm">No pending leave requests.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Employee ID</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Days</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Decision</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.map((req) => (
                  <Table.Tr key={req.id}>
                    <Table.Td>{req.employee_id}</Table.Td>
                    <Table.Td>{req.leave_type_code}</Table.Td>
                    <Table.Td>{`${req.start_date} to ${req.end_date}`}</Table.Td>
                    <Table.Td>{req.total_days}</Table.Td>
                    <Table.Td>{req.reason}</Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          loading={decideMutation.isPending}
                          onClick={() => decideMutation.mutate({ id: req.id, decision: "APPROVE" })}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          loading={decideMutation.isPending}
                          onClick={() => decideMutation.mutate({ id: req.id, decision: "REJECT" })}
                        >
                          Reject
                        </Button>
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
