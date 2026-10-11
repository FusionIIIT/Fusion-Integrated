import { useState } from "react";
import {
  Alert, Button, Card, Checkbox, Container, Group, Select, Stack, Text,
  TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances, useLeaveTypes, useSubmitLeave } from "../api/hooks";

/** The form a request is composed on; every rule is still enforced server-side. */
export default function ApplyLeavePage() {
  const types = useLeaveTypes();
  const balances = useBalances();
  const submit = useSubmitLeave();

  const [typeId, setTypeId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState(false);
  const [halfPart, setHalfPart] = useState<string | null>("first");
  const [reason, setReason] = useState("");

  if (types.error) {
    return <Container size="md"><ErrorState error={types.error} /></Container>;
  }

  const selected = types.data?.find((t) => String(t.id) === typeId);
  const balance = balances.data?.find(
    (b) => b.leave_type_code === selected?.code);
  const singleDay = startDate !== "" && startDate === endDate;

  function onSubmit() {
    if (!selected || !startDate || !endDate) return;
    submit.mutate(
      {
        leave_type_id: selected.id,
        start_date: startDate,
        end_date: endDate,
        is_half_day: halfDay && singleDay,
        half_day_part: halfDay && singleDay ? (halfPart ?? "") : "",
        reason,
      },
      {
        onSuccess: (application) => {
          notifications.show({
            color: "green", title: "Request submitted",
            message: `Leave from ${application.start_date} to ${application.end_date}`
              + ` is now pending.`,
          });
          setStartDate(""); setEndDate(""); setReason(""); setHalfDay(false);
        },
        onError: (error) => notifications.show({
          color: "red", title: "Could not submit", message: errorMessage(error),
        }),
      },
    );
  }

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Weekends and institute holidays are not counted"
      />
      <Card padding="lg">
        <Stack>
          <Select
            label="Leave type" required placeholder="Pick a type"
            data={(types.data ?? []).map((t) => ({
              value: String(t.id), label: `${t.code} — ${t.name}`,
            }))}
            value={typeId} onChange={setTypeId}
            disabled={types.isPending}
          />
          {balance && (
            <Text size="sm" c="dimmed">
              {balance.available_days} day(s) available · {balance.used_days} used
              of {balance.entitled_days}
            </Text>
          )}
          {selected?.requires_reason && (
            <Alert color="blue" variant="light">
              {selected.name} requires a reason; the approver reads it.
            </Alert>
          )}
          <Group grow align="flex-start">
            <TextInput
              label="From" type="date" required value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)}
            />
            <TextInput
              label="To" type="date" required value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)}
            />
          </Group>
          {selected?.allows_half_day && singleDay && (
            <Group>
              <Checkbox
                label="Half day" checked={halfDay}
                onChange={(e) => setHalfDay(e.currentTarget.checked)}
              />
              {halfDay && (
                <Select
                  aria-label="Which half" data={[
                    { value: "first", label: "First half" },
                    { value: "second", label: "Second half" },
                  ]}
                  value={halfPart} onChange={setHalfPart} w={160}
                />
              )}
            </Group>
          )}
          <Textarea
            label={selected?.requires_reason ? "Reason (required)" : "Reason"}
            value={reason} onChange={(e) => setReason(e.currentTarget.value)}
            minRows={2}
          />
          <Group justify="flex-end">
            <Button
              loading={submit.isPending}
              disabled={!selected || !startDate || !endDate}
              onClick={onSubmit}
            >
              Submit request
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
