import { useState } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useApprovalsInbox, useUnitHeadDecision } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function ApprovalsPage() {
  const { data, isPending, error } = useApprovalsInbox();
  const [decisionFor, setDecisionFor] = useState<number | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function approve(app: LeaveApplication) {
    notifications.show({
      color: "blue", title: "Approved",
      message: `Your leave application has been approved.`,
    });
  }

  function reject(app: LeaveApplication) {
    notifications.show({
      color: "red", title: "Rejected",
      message: `Your leave application has been rejected.`,
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Approvals Inbox"
        subtitle="Requests awaiting your decision"
      />
      {data?.results.length === 0 ? (
        <Card padding="lg">
          <Text>No pending approvals</Text>
        </Card>
      ) : (
        <Card padding="lg">
          <Stack gap="md">
            {data.results.map((app) => (
              <Card key={app.id} padding="sm" radius="md">
                <Stack gap="xs">
                  <Group justify="space-between">
                    <Text fw={600}>{app.leave_type.replace(/_/g, " ")}</Text>
                    <StatusBadge status={app.status} />
                  </Group>
                  <Text size="sm" c="dimmed">
                    {new Date(app.start_date).toLocaleDateString()} - {new Date(app.end_date).toLocaleDateString()}
                  </Text>
                  <Text size="sm">{app.reason}</Text>
                  <Group justify="flex-end" gap="xs" mt="xs">
                    <Button
                      color="blue" leftIcon={<FaCheck />}
                      onClick={() => approve(app)}
                    >
                      Approve
                    </Button>
                    <Button
                      color="red" leftIcon={<FaTimes />}
                      onClick={() => reject(app)}
                    >
                      Reject
                    </Button>
                  </Group>
                </Stack>
              </Card>
            ))}
          </Stack>
        </Card>
      )}
    </Container>
  );
}
