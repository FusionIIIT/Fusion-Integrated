import { useState } from "react";
import { Button, Card, Container, Group, NumberInput, Select, Stack, Textarea } from "@mantine/core";
import { DatePickerInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaPaperPlane } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateLeaveRequest, useLeaveTypes } from "../api/hooks";
import type { LeaveType } from "../api/types";

export default function ApplyLeavePage() {
  const { data: types, isLoading: typesLoading, error: typesError } = useLeaveTypes();
  const create = useCreateLeaveRequest();

  const [leaveType, setLeaveType] = useState<string | null>(null);
  const [start, setStart] = useState<Date | null>(null);
  const [end, setEnd] = useState<Date | null>(null);
  const [halfDay, setHalfDay] = useState<string>("none");
  const [reason, setReason] = useState("");
  const [substitute, setSubstitute] = useState<number | "">("");

  if (typesError) return <Container size="lg"><ErrorState error={typesError} /></Container>;

  const selectedType = (types ?? []).find((t: LeaveType) => String(t.id) === leaveType);

  function submit() {
    if (!leaveType || !start || !end) {
      notifications.show({ color: "red", title: "Missing fields", message: "Type and dates are required." });
      return;
    }
    create.mutate(
      {
        leave_type: Number(leaveType),
        start_date: start.toISOString().slice(0, 10),
        end_date: end.toISOString().slice(0, 10),
        half_day: halfDay as "none" | "first" | "second",
        reason,
        substitute_user_id: substitute === "" ? null : Number(substitute),
      } as never,
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Submitted", message: "Leave request created." });
          setReason("");
        },
        onError: (e) => notifications.show({ color: "red", title: "Could not submit", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="lg">
      <PageHeader title="Apply for Leave" subtitle="Submit a new leave application." />
      <Card padding="lg">
        <Stack gap="md">
          <Select
            label="Leave type"
            placeholder="Select type"
            data={(types ?? []).map((t: LeaveType) => ({ value: String(t.id), label: `${t.code} - ${t.name}` }))}
            value={leaveType}
            onChange={setLeaveType}
            disabled={typesLoading}
            required
          />
          <Group grow>
            <DatePickerInput label="Start date" value={start} onChange={setStart} required />
            <DatePickerInput label="End date" value={end} onChange={setEnd} required />
          </Group>
          {selectedType?.allow_half_day && (
            <Select
              label="Half day"
              data={[{ value: "none", label: "Full day" }, { value: "first", label: "First half" }, { value: "second", label: "Second half" }]}
              value={halfDay}
              onChange={(v) => setHalfDay(v ?? "none")}
            />
          )}
          <Textarea label="Reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} required />
          <NumberInput label="Substitute (user id, optional)" value={substitute} onChange={(v) => setSubstitute(v === "" ? "" : Number(v))} />
          <Group justify="flex-end">
            <Button leftSection={<FaPaperPlane size={12} />} loading={create.isPending} onClick={submit}>
              Submit
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}