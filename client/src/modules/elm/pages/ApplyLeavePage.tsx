import { useState } from "react";
import {
  Button,
  Checkbox,
  Container,
  Group,
  NumberInput,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { notifications } from "@mantine/notifications";
import { useApplyLeave } from "../api/hooks";
import type { LeaveType } from "../api/types";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const applyMutation = useApplyLeave();

  const [leaveType, setLeaveType] = useState<LeaveType>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [substituteId, setSubstituteId] = useState<number | undefined>(undefined);
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [halfDay, setHalfDay] = useState(false);
  const [halfDayType, setHalfDayType] = useState<string>("first_half");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate) {
      notifications.show({
        title: "Validation Error",
        message: "Please specify start and end dates.",
        color: "red",
      });
      return;
    }

    applyMutation.mutate(
      {
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        reason,
        substitute_id: substituteId,
        is_station_leave: isStationLeave,
        station_address: stationAddress,
        half_day: halfDay,
        half_day_type: halfDay ? halfDayType : undefined,
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Success",
            message: "Leave application submitted successfully.",
            color: "green",
          });
          navigate("../mine");
        },
        onError: (err: any) => {
          notifications.show({
            title: "Error submitting application",
            message: err?.response?.data ? JSON.stringify(err.response.data) : "Submission failed",
            color: "red",
          });
        },
      }
    );
  };

  return (
    <Container size="md" py="md">
      <Paper withBorder p="xl" radius="sm">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <div>
              <Title order={2}>Apply for Leave</Title>
              <Text c="dimmed" size="sm">Submit a new leave application</Text>
            </div>

            <Select
              label="Leave Type"
              required
              data={[
                { value: "CL", label: "Casual Leave (CL)" },
                { value: "RH", label: "Restricted Holiday (RH)" },
                { value: "SCL", label: "Special Casual Leave (SCL)" },
                { value: "EL", label: "Earned Leave (EL)" },
                { value: "COL", label: "Commuted Leave (COL)" },
                { value: "VL", label: "Vacation Leave (VL)" },
              ]}
              value={leaveType}
              onChange={(val) => setLeaveType((val as LeaveType) || "CL")}
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <TextInput
                label="End Date"
                type="date"
                required
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </Group>

            {leaveType === "CL" && (
              <Group>
                <Checkbox
                  label="Half Day CL"
                  checked={halfDay}
                  onChange={(e) => setHalfDay(e.currentTarget.checked)}
                />
                {halfDay && (
                  <Select
                    label="Half Day Session"
                    data={[
                      { value: "first_half", label: "First Half" },
                      { value: "second_half", label: "Second Half" },
                    ]}
                    value={halfDayType}
                    onChange={(val) => setHalfDayType(val || "first_half")}
                  />
                )}
              </Group>
            )}

            <NumberInput
              label="Substitute User ID (Optional)"
              description="Nominate an employee to handle duties during leave"
              value={substituteId}
              onChange={(val) => setSubstituteId(typeof val === "number" ? val : undefined)}
            />

            <Checkbox
              label="Station Leave (leaving Jabalpur)"
              checked={isStationLeave}
              onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
            />

            {isStationLeave && (
              <TextInput
                label="Station Address & Contact Details"
                placeholder="Address during station leave"
                value={stationAddress}
                onChange={(e) => setStationAddress(e.target.value)}
              />
            )}

            <Textarea
              label="Reason for Leave"
              placeholder="Provide justification or reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              minRows={3}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("../mine")}>
                Cancel
              </Button>
              <Button type="submit" loading={applyMutation.isPending}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Container>
  );
}
