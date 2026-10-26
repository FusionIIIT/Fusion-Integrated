import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Card, Container, Group, Loader, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type ApprovalTask = {
  id: number;
  stage: string;
  decision_mode: "RECOMMEND" | "VERIFY" | "FINAL";
  request: {
    id: number;
    leave_type_code: string;
    requested_start_date: string;
    requested_end_date: string;
    total_days: string;
  };
};

export default function ApprovalsPage() {
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["elm", "approvals"],
    queryFn: async () => (await http.get<{ results: ApprovalTask[] }>("/leave/approvals")).data.results,
  });
  const decide = useMutation({
    mutationFn: async (input: { requestId: number; action: string }) =>
      http.post("/leave/requests/" + input.requestId + "/decision", { action: input.action }),
    onSuccess: async () => {
      await cache.invalidateQueries({ queryKey: ["elm", "approvals"] });
      notifications.show({ title: "Decision recorded", message: "The next workflow step has been updated.", color: "green" });
    },
  });

  return (
    <Container size="xl">
      <PageHeader title="Leave approvals" subtitle="Review only the requests assigned to your Fusion account" />
      {query.isPending && <Loader />}
      {(query.error || decide.error) && <Alert color="red" title="Could not complete this action">{errorMessage(query.error ?? decide.error)}</Alert>}
      <Stack>
        {(query.data ?? []).map((task) => {
          const act = (action: string) => decide.mutate({ requestId: task.request.id, action });
          return <Card key={task.id} withBorder>
            <Group justify="space-between" align="flex-start">
              <Stack gap={2}>
                <Text fw={700}>{task.request.leave_type_code} leave · {task.request.total_days} days</Text>
                <Text size="sm">{task.request.requested_start_date} to {task.request.requested_end_date}</Text>
                <Text size="sm" c="dimmed">{task.stage.replaceAll("_", " ")} · {task.decision_mode.toLowerCase()}</Text>
              </Stack>
              <Group>
                {task.decision_mode === "RECOMMEND" && <>
                  <Button loading={decide.isPending} onClick={() => act("RECOMMEND")}>Recommend</Button>
                  <Button color="red" variant="light" loading={decide.isPending} onClick={() => act("NOT_RECOMMENDED")}>Do not recommend</Button>
                </>}
                {task.decision_mode === "VERIFY" && <Button loading={decide.isPending} onClick={() => act("VERIFY")}>Verify</Button>}
                {task.decision_mode === "FINAL" && <>
                  <Button color="green" loading={decide.isPending} onClick={() => act("APPROVE")}>Approve</Button>
                  <Button color="red" variant="light" loading={decide.isPending} onClick={() => act("REJECT")}>Reject</Button>
                </>}
              </Group>
            </Group>
          </Card>;
        })}
        {!query.isPending && !query.error && (query.data ?? []).length === 0 &&
          <Card withBorder><Text>No leave requests are waiting for your decision.</Text></Card>}
      </Stack>
    </Container>
  );
}
