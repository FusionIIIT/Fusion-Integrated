import { useState } from "react";
import {
  Button, Card, Checkbox, Container, Group, Select, Stack, TextInput, Textarea
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplyLeave, useLeaveTypes } from "../api/hooks";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const { data: leaveTypes, isPending: loadingTypes } = useLeaveTypes();
  const applyMutation = useApplyLeave();

  const [leaveTypeId, setLeaveTypeId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDayType, setHalfDayType] = useState<string>("FULL");
  const [reason, setReason] = useState("");
  const [isStation, setIsStation] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leaveTypeId || !startDate || !endDate) {
      notifications.show({ title: "Incomplete form", message: "Fill required fields", color: "orange" });
      return;
    }

    try {
      await applyMutation.mutateAsync({
        leave_type_id: Number(leaveTypeId),
        start_date: startDate,
        end_date: endDate,
        half_day_type: halfDayType,
        reason,
        is_station_leave: isStation,
      });
      notifications.show({
        title: "Application submitted",
        message: "Your leave application has been recorded.",
        color: "teal",
      });
      navigate("/elm/mine");
    } catch (err: any) {
      notifications.show({
        title: "Submission failed",
        message: err.message || "Could not submit application",
        color: "red",
      });
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new casual, earned, vacation, or medical leave application"
      />

      <Card padding="lg" shadow="xs" radius="md">
        <form onSubmit={handleSubmit}>
          <Stack>
            <Select
              label="Leave Type"
              placeholder="Select leave category"
              required
              data={leaveTypes?.map((t) => ({ value: String(t.id), label: `${t.code} - ${t.name}` })) ?? []}
              value={leaveTypeId}
              onChange={setLeaveTypeId}
              disabled={loadingTypes}
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.currentTarget.value)}
              />
              <TextInput
                label="End Date"
                type="date"
                required
                value={endDate}
                onChange={(e) => setEndDate(e.currentTarget.value)}
              />
            </Group>

            <Select
              label="Day Duration"
              data={[
                { value: "FULL", label: "Full Day" },
                { value: "FIRST_HALF", label: "First Half Day" },
                { value: "SECOND_HALF", label: "Second Half Day" },
              ]}
              value={halfDayType}
              onChange={(val) => setHalfDayType(val || "FULL")}
            />

            <Checkbox
              label="Station Leave (outside Jabalpur during leave interval)"
              checked={isStation}
              onChange={(e) => setIsStation(e.currentTarget.checked)}
            />

            <Textarea
              label="Purpose / Reason"
              placeholder="Detail the reason for your leave"
              required
              minRows={3}
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/elm/mine")}>Cancel</Button>
              <Button type="submit" loading={applyMutation.isPending}>Submit Application</Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
