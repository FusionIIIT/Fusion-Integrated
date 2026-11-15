import { Button, Card, Container, Group, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApply } from "../api/hooks";
import { EMPTY_LEAVE, LeaveForm, missingReason } from "../components/LeaveForm";

export default function ApplyPage() {
  const [value, setValue] = useState(EMPTY_LEAVE);
  const apply = useApply();
  const navigate = useNavigate();
  const missing = missingReason(value);

  function submit() {
    apply.mutate(value, {
      onSuccess: () => {
        notifications.show({ color: "green", title: "Leave submitted",
          message: "Track it under My Leave." });
        navigate("../mine");
      },
      onError: (e) => notifications.show({ color: "red", title: "Could not submit",
        message: errorMessage(e) }),
    });
  }

  return (
    <Container size="md">
      <PageHeader title="Apply for Leave"
        subtitle="Balances, overlap and calendar rules are checked when you submit" />
      <Card withBorder padding="lg">
        <LeaveForm value={value} onChange={setValue} />
        <Group justify="space-between" mt="lg">
          <Text size="xs" c="dimmed">{missing}</Text>
          <Button onClick={submit} loading={apply.isPending} disabled={!!missing}>
            Submit application
          </Button>
        </Group>
      </Card>
    </Container>
  );
}
