import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Text,
  Title,
} from "@mantine/core";

const initialApprovals = [
  {
    id: 1,
    employee: "Rahul Kumar",
    type: "Casual Leave",
    dates: "2026-10-25 to 2026-10-26",
    reason: "Family function",
  },
  {
    id: 2,
    employee: "Meera Singh",
    type: "Earned Leave",
    dates: "2026-11-03 to 2026-11-05",
    reason: "Travel and rest",
  },
];

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState(initialApprovals);

  const handleDecision = (id: number) => {
    setApprovals((current) => current.filter((item) => item.id !== id));
  };

  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <Group justify="space-between">
          <div>
            <Title order={2}>Approvals</Title>
            <Text c="dimmed" size="sm">
              Review pending leave requests that are waiting for your decision.
            </Text>
          </div>
          <Badge variant="light" color="orange" size="lg">
            {approvals.length} pending
          </Badge>
        </Group>

        {approvals.length === 0 ? (
          <Card withBorder radius="md" padding="lg">
            <Text c="dimmed">No leave requests are pending your approval.</Text>
          </Card>
        ) : (
          approvals.map((request) => (
            <Card key={request.id} withBorder radius="md" padding="lg">
              <Stack gap="sm">
                <Group justify="space-between">
                  <div>
                    <Text fw={600}>{request.employee}</Text>
                    <Text size="sm" c="dimmed">
                      {request.type} · {request.dates}
                    </Text>
                  </div>
                  <Badge variant="light" color="yellow">Pending</Badge>
                </Group>

                <Text size="sm">Reason: {request.reason}</Text>

                <Group justify="flex-end">
                  <Button variant="default" onClick={() => handleDecision(request.id)}>
                    Reject
                  </Button>
                  <Button onClick={() => handleDecision(request.id)}>
                    Approve
                  </Button>
                </Group>
              </Stack>
            </Card>
          ))
        )}
      </Stack>
    </Container>
  );
}
