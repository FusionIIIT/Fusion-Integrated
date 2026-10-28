import { Alert, Button, Card, Group, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import {
  useDecideLeaveTask, useLeaveTasks, useSubstituteRequests, useSubstituteResponse,
} from "../api/hooks";

export default function LeaveApprovalsPage() {
  const tasks = useLeaveTasks();
  const substitutes = useSubstituteRequests();
  const decide = useDecideLeaveTask();
  const respond = useSubstituteResponse();
  const [notes, setNotes] = useState<Record<number, string>>({});
  const fail = (error: unknown) =>
    notifications.show({ color: "red", message: errorMessage(error) });

  if (tasks.isError && substitutes.isError) {
    return <Alert color="red" title="Unable to load assigned requests">
      {errorMessage(tasks.error)}
    </Alert>;
  }

  return (
    <Stack>
      <Title order={2}>Leave Approvals</Title>
      {substitutes.data?.results.map((request) => (
        <Card key={`substitute-${request.id}`} withBorder>
          <Group justify="space-between">
            <div>
              <Text fw={700}>Substitute request: {request.category}</Text>
              <Text size="sm">{request.starts_on} – {request.ends_on}</Text>
            </div>
            <Group>
              <Button
                onClick={() => respond.mutate(
                  { id: request.id, accept: true },
                  { onError: fail },
                )}
              >Accept</Button>
              <Button
                color="red"
                variant="light"
                onClick={() => respond.mutate(
                  { id: request.id, accept: false },
                  { onError: fail },
                )}
              >Decline</Button>
            </Group>
          </Group>
        </Card>
      ))}
      {tasks.data?.results.map((task) => (
        <Card key={task.id} withBorder>
          <Stack>
            <div>
              <Text fw={700}>
                {task.request.category} {task.request.request_type} request
              </Text>
              <Text size="sm">
                Employee {task.request.applicant_user_id}: {task.request.starts_on}
                {" – "}{task.request.ends_on}; {task.request.requested_days} days
              </Text>
              <Text size="sm">{task.request.purpose}</Text>
            </div>
            <TextInput
              label="Decision note (required when rejecting)"
              value={notes[task.id] ?? ""}
              onChange={(event) => setNotes({
                ...notes, [task.id]: event.currentTarget.value,
              })}
            />
            <Group>
              {(task.is_final
                ? ["approve", "reject"] as const
                : ["recommend", "not_recommend"] as const
              ).map((action) => (
                <Button
                  key={action}
                  color={action.includes("reject") || action === "not_recommend"
                    ? "red" : "blue"}
                  loading={decide.isPending}
                  onClick={() => decide.mutate(
                    {
                      requestId: task.request.id,
                      taskId: task.id,
                      action,
                      note: notes[task.id] ?? "",
                    },
                    {
                      onError: fail,
                      onSuccess: () =>
                        notifications.show({ message: "Decision recorded." }),
                    },
                  )}
                >
                  {action.replaceAll("_", " ")}
                </Button>
              ))}
            </Group>
          </Stack>
        </Card>
      ))}
      {tasks.data?.results.length === 0 && substitutes.data?.results.length === 0 && (
        <Text c="dimmed">There are no requests assigned to you.</Text>
      )}
    </Stack>
  );
}
