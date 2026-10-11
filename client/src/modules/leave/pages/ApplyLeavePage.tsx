import { useState } from "react";
import {
  Button, Card, Checkbox, Container, Group, NumberInput, Select, Stack,
  Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApply, useBalances } from "../api/hooks";
import type { LeaveType } from "../api/types";

const TYPES: { value: LeaveType; label: string }[] = [
  { value: "CL", label: "CL — Casual Leave" },
  { value: "RH", label: "RH — Restricted Holiday" },
  { value: "SCL", label: "SCL — Special Casual Leave" },
  { value: "EL", label: "EL — Earned Leave" },
  { value: "COL", label: "COL — Commuted Leave" },
  { value: "VL", label: "VL — Vacation Leave" },
];

/** EL-UC-001. Station Leave is part of this form, not a separate request. */
export default function ApplyLeavePage() {
  const apply = useApply();
  const { data: balances } = useBalances();
  const [leaveType, setLeaveType] = useState<LeaveType>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState("");
  const [reason, setReason] = useState("");
  const [stationLeave, setStationLeave] = useState(false);
  const [stationPlace, setStationPlace] = useState("");
  const [substitute, setSubstitute] = useState<number | "">("");

  function submit() {
    apply.mutate(
      {
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate || startDate,
        half_day: halfDay,
        reason,
        station_leave: stationLeave,
        station_place: stationPlace,
        substitute_user_id: substitute === "" ? null : Number(substitute),
      },
      {
        onSuccess: () => notifications.show({
          color: "green", title: "Submitted",
          message: "Your leave request has entered approval routing.",
        }),
        onError: (e) => notifications.show({
          color: "red", title: "Could not submit", message: errorMessage(e),
        }),
      },
    );
  }

  const available = balances?.find((b) => b.leave_type === leaveType)?.available;

  return (
    <Container size="sm">
      <PageHeader
        title="Apply for Leave"
        subtitle="One application per request — category, period, and Station Leave together"
      />
      <Card padding="lg">
        <Stack>
          <Select
            label="Leave category" data={TYPES} value={leaveType}
            allowDeselect={false}
            description={available ? `${available} day(s) available` : undefined}
            onChange={(v) => setLeaveType((v ?? "CL") as LeaveType)}
          />
          <Group grow>
            <TextInput
              label="From" type="date" value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)}
            />
            <TextInput
              label="To" type="date" value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)}
            />
          </Group>
          {leaveType === "CL" && (
            <Select
              label="Half day" clearable value={halfDay}
              data={[{ value: "first", label: "First half" },
                     { value: "second", label: "Second half" }]}
              description="An approved half day consumes 0.5 CL"
              onChange={(v) => setHalfDay(v ?? "")}
            />
          )}
          <Textarea
            label="Purpose / reason" minRows={3} value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />
          <Checkbox
            label="I will be outside Jabalpur (Station Leave)"
            checked={stationLeave}
            onChange={(e) => setStationLeave(e.currentTarget.checked)}
          />
          {stationLeave && (
            <TextInput
              label="Place of stay" value={stationPlace}
              onChange={(e) => setStationPlace(e.currentTarget.value)}
            />
          )}
          <NumberInput
            label="Substitute employee id" value={substitute}
            description="Leave empty if responsibility coverage is not required"
            onChange={(v) => setSubstitute(v === "" ? "" : Number(v))}
          />
          <Group justify="flex-end">
            <Button
              onClick={submit} loading={apply.isPending}
              disabled={!startDate || !leaveType}
            >
              Submit request
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
