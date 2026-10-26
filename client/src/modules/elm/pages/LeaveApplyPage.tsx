import { useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Select,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateLeaveApplication, useLeaveTypes } from "../api/hooks";

export default function LeaveApplyPage() {
  const types = useLeaveTypes();
  const createApp = useCreateLeaveApplication();

  const [leaveTypeCode, setLeaveTypeCode] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState(false);
  const [stationLeave, setStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [reason, setReason] = useState("");

  function handleSubmit() {
    if (!leaveTypeCode || !startDate || !endDate) return;
    createApp.mutate(
      {
        leave_type_code: leaveTypeCode,
        start_date: startDate,
        end_date: endDate,
        half_day: halfDay,
        station_leave: stationLeave,
        station_address: stationAddress,
        reason,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Application submitted",
            message: "Your leave request has been submitted.",
          });
          setReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Submission failed",
            message: errorMessage(err),
          });
        },
      },
    );
  }

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new leave application"
      />
      <Card withBorder padding="lg">
        <Stack gap="md">
          <Select
            label="Leave Type"
            placeholder="Select leave category"
            data={(types.data?.results ?? []).map((t) => ({
              value: t.code,
              label: `${t.code} - ${t.name}`,
            }))}
            value={leaveTypeCode}
            onChange={setLeaveTypeCode}
          />
          <Group grow>
            <TextInput
              type="date"
              label="Start Date"
              value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)}
            />
            <TextInput
              type="date"
              label="End Date"
              value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)}
            />
          </Group>
          <Checkbox
            label="Half-day leave"
            checked={halfDay}
            onChange={(e) => setHalfDay(e.currentTarget.checked)}
          />
          <Checkbox
            label="Station leave required (outside Jabalpur)"
            checked={stationLeave}
            onChange={(e) => setStationLeave(e.currentTarget.checked)}
          />
          {stationLeave && (
            <TextInput
              label="Outstation Address"
              value={stationAddress}
              onChange={(e) => setStationAddress(e.currentTarget.value)}
            />
          )}
          <Textarea
            label="Reason"
            minRows={3}
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button
              onClick={handleSubmit}
              loading={createApp.isPending}
              disabled={!leaveTypeCode || !startDate || !endDate}
            >
              Submit Application
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
