import { Alert, Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useTasks } from "../api";

export default function TasksPage() {
  const tasks = useTasks();
  if (tasks.error) return <Container size="md"><ErrorState error={tasks.error} /></Container>;
  return <Container size="md">
    <PageHeader title="Leave tasks" subtitle="Review and route leave applications assigned to your role." />
    <Stack>
      {(tasks.data?.results ?? []).length === 0 && <Alert color="gray">There are no pending tasks assigned to you.</Alert>}
      {(tasks.data?.results ?? []).map((task) => <Card withBorder key={task.id}>
        <Group justify="space-between" align="flex-start"><div>
        <Text fw={600}>Request #{task.request_id} · {task.category_code}</Text>
          <Text size="sm" c="dimmed">{task.role.replaceAll("_", " ")} · step {task.sequence}</Text>
        </div>
        <Group>{task.role === "unit_head" && !["CL", "RH"].includes(task.category_code) ? <>
          <Button size="xs" variant="light" onClick={() => tasks.decide.mutate({ id: task.id, decision: "recommended" }, { onError: (e) => notifications.show({ color: "red", title: "Could not record review", message: errorMessage(e) }) })}>Recommend</Button>
          <Button size="xs" color="red" variant="light" onClick={() => tasks.decide.mutate({ id: task.id, decision: "not_recommended" }, { onError: (e) => notifications.show({ color: "red", title: "Could not record review", message: errorMessage(e) }) })}>Not recommended</Button>
        </> : <>
          <Button size="xs" color="green" onClick={() => tasks.decide.mutate({ id: task.id, decision: task.role === "establishment" ? "forwarded" : "approved" }, { onError: (e) => notifications.show({ color: "red", title: "Could not decide request", message: errorMessage(e) }) })}>{task.role === "establishment" ? "Forward" : "Approve"}</Button>
          {task.role !== "establishment" && <Button size="xs" color="red" variant="light" onClick={() => tasks.decide.mutate({ id: task.id, decision: "rejected" }, { onError: (e) => notifications.show({ color: "red", title: "Could not decide request", message: errorMessage(e) }) })}>Reject</Button>}
        </>}</Group></Group>
      </Card>)}
    </Stack>
  </Container>;
}
