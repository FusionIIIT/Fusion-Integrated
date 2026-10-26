import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Card, Container, Group, Loader, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type SubstituteTask = {
  id: number;
  leave_type_code: string;
  requested_start_date: string;
  requested_end_date: string;
  total_days: string;
};

export default function SubstitutionsPage() {
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["elm", "substitutions"],
    queryFn: async () => (await http.get<{ results: SubstituteTask[] }>("/leave/substitutions")).data.results,
  });
  const respond = useMutation({
    mutationFn: async (input: { id: number; action: "ACCEPT" | "DECLINE" }) =>
      http.post("/leave/requests/" + input.id + "/substitute-response", { action: input.action }),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["elm", "substitutions"] });
      notifications.show({ title: "Response recorded", message: "The employee's request has been updated.", color: "green" });
    },
  });

  return (
    <Container size="xl">
      <PageHeader title="Substitute requests" subtitle="Accept or decline leave requests assigned to you" />
      {query.isPending && <Loader />}
      {(query.error || respond.error) && <Alert color="red" title="Could not complete this action">{errorMessage(query.error ?? respond.error)}</Alert>}
      <Stack>
        {(query.data ?? []).map((task) => (
          <Card key={task.id} withBorder>
            <Group justify="space-between">
              <Stack gap={2}>
                <Text fw={700}>{task.leave_type_code} leave · {task.total_days} days</Text>
                <Text size="sm">{task.requested_start_date} to {task.requested_end_date}</Text>
              </Stack>
              <Group>
                <Button loading={respond.isPending} onClick={() => respond.mutate({ id: task.id, action: "ACCEPT" })}>Accept</Button>
                <Button color="red" variant="light" loading={respond.isPending} onClick={() => respond.mutate({ id: task.id, action: "DECLINE" })}>Decline</Button>
              </Group>
            </Group>
          </Card>
        ))}
        {!query.isPending && !query.error && (query.data ?? []).length === 0 &&
          <Card withBorder><Text>No substitute requests are waiting for you.</Text></Card>}
      </Stack>
    </Container>
  );
}
