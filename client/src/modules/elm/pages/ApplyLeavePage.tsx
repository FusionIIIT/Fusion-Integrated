import { useState } from "react";
import { Button, Card, Container, Select, Stack, Text, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { errorMessage } from "../../../lib/http";
import { useLeaveTypes, useApplyLeave } from "../../../modules/elm/api";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ApplyLeavePage() {
  const { data: leaveTypes, isPending: typesPending } = useLeaveTypes();
  const [type, setType] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [reason, setReason] = useState("");
  const applyLeave = useApplyLeave();

  const handleSubmit = () => {
    if (!type || !from || !to || !reason) return;
    applyLeave.mutate(
      { leave_type: Number(type), start_date: from, end_date: to, reason },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Submitted", message: "Your leave application has been submitted.",
          });
          setType("");
          setFrom("");
          setTo("");
          setReason("");
        },
        onError: (e: Error) => notifications.show({
          color: "red", title: "Could not submit", message: errorMessage(e),
        }),
      },
    );
  };

  return (
    <Container size="md">
      <PageHeader title="Apply for Leave" subtitle="Submit a new leave application" />
      <Card padding="lg">
        <Stack>
          <Select
            value={type}
            onChange={(v) => setType(v ?? "")}
            disabled={typesPending}
            data={leaveTypes?.map(t => ({ value: t.id.toString(), label: `${t.name} (${t.code})` })) || []}
          />
          <TextInput type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
          <TextInput type="date" value={to} onChange={(e) => setTo(e.target.value)} />
          {from && to && (
            <Text size="sm" c="dimmed">
              Days: {Math.round((new Date(to).getTime() - new Date(from).getTime()) / 86400000) + 1}
            </Text>
          )}
          <Textarea value={reason} onChange={(e) => setReason(e.target.value)} required />
          <Button
            size="xs" variant="subtle" color="gray"
            loading={applyLeave.isPending}
            onClick={handleSubmit}
            disabled={!type || !from || !to || !reason}
          >
            Submit application
          </Button>
        </Stack>
      </Card>
    </Container>
  );
}
