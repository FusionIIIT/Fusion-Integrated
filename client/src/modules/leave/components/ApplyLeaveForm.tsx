import {
  Button,
  Card,
  Checkbox,
  Divider,
  Grid,
  Group,
  Select,
  Stack,
  TextInput,
  Textarea,
  Title,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { useSubmitApplication } from "../api/hooks";
import type { CreateLeavePayload, LeaveCategory } from "../api/types";

export function ApplyLeaveForm() {
  const navigate = useNavigate();
  const submitMutation = useSubmitApplication();

  const [leaveType, setLeaveType] = useState<LeaveCategory>("CL");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [halfDayType, setHalfDayType] = useState<"FULL" | "FIRST_HALF" | "SECOND_HALF">("FULL");
  const [reason, setReason] = useState<string>("");
  const [substituteUserId, setSubstituteUserId] = useState<number | string>("");

  const [isStationLeave, setIsStationLeave] = useState<boolean>(false);
  const [stationDeparture, setStationDeparture] = useState<string>("");
  const [stationArrival, setStationArrival] = useState<string>("");
  const [stationAddress, setStationAddress] = useState<string>("");
  const [contactNumber, setContactNumber] = useState<string>("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!startDate || !endDate) {
      notifications.show({ title: "Validation Error", message: "Start date and end date are required.", color: "red" });
      return;
    }

    if (!reason.trim()) {
      notifications.show({ title: "Validation Error", message: "Please provide a reason for the leave.", color: "red" });
      return;
    }

    const payload: CreateLeavePayload = {
      leave_type: leaveType,
      start_date: startDate,
      end_date: endDate,
      half_day_type: leaveType === "CL" ? halfDayType : "FULL",
      reason,
      substitute_user_id: substituteUserId ? Number(substituteUserId) : null,
      is_station_leave: isStationLeave,
      station_departure_date: isStationLeave && stationDeparture ? new Date(stationDeparture).toISOString() : null,
      station_arrival_date: isStationLeave && stationArrival ? new Date(stationArrival).toISOString() : null,
      station_address: isStationLeave ? stationAddress : "",
      contact_number: isStationLeave ? contactNumber : "",
    };

    try {
      await submitMutation.mutateAsync(payload);
      notifications.show({
        title: "Leave Application Submitted",
        message: "Your application has been registered and routed according to policy.",
        color: "green",
      });
      navigate("/leave/mine");
    } catch (err) {
      notifications.show({
        title: "Application Failed",
        message: errorMessage(err),
        color: "red",
      });
    }
  };

  return (
    <Card withBorder padding="lg" radius="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Title order={4}>Submit Leave Application</Title>

          <Grid>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <Select
                label="Leave Category"
                required
                value={leaveType}
                onChange={(val) => setLeaveType((val as LeaveCategory) || "CL")}
                data={[
                  { value: "CL", label: "Casual Leave (CL)" },
                  { value: "RH", label: "Restricted Holiday (RH)" },
                  { value: "SCL", label: "Special Casual Leave (SCL)" },
                  { value: "EL", label: "Earned Leave (EL)" },
                  { value: "COL", label: "Commuted Leave (COL)" },
                  { value: "VL", label: "Vacation Leave (VL)" },
                ]}
              />
            </Grid.Col>

            {leaveType === "CL" && (
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Select
                  label="Day Portion"
                  value={halfDayType}
                  onChange={(val) => setHalfDayType((val as any) || "FULL")}
                  data={[
                    { value: "FULL", label: "Full Day" },
                    { value: "FIRST_HALF", label: "First Half (0.5 day)" },
                    { value: "SECOND_HALF", label: "Second Half (0.5 day)" },
                  ]}
                />
              </Grid.Col>
            )}

            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput
                label="Start Date"
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput
                label="End Date"
                type="date"
                required
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </Grid.Col>

            <Grid.Col span={12}>
              <Textarea
                label="Reason for Leave"
                placeholder="State the purpose of your leave request"
                required
                minRows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput
                label="Nominated Substitute User ID"
                placeholder="Enter colleague User ID (optional)"
                type="number"
                value={substituteUserId}
                onChange={(e) => setSubstituteUserId(e.target.value)}
              />
              <Text size="xs" c="dimmed" mt={2}>
                If specified, workflow will wait for substitute acceptance (BR-EL-014/015).
              </Text>
            </Grid.Col>
          </Grid>

          <Divider label="Station Leave Permission (BR-EL-013)" labelPosition="left" />

          <Checkbox
            label="Request permission to leave station (outside Jabalpur)"
            checked={isStationLeave}
            onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
          />

          {isStationLeave && (
            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label="Departure Date & Time"
                  type="datetime-local"
                  value={stationDeparture}
                  onChange={(e) => setStationDeparture(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label="Arrival Date & Time"
                  type="datetime-local"
                  value={stationArrival}
                  onChange={(e) => setStationArrival(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label="Outstation Address"
                  placeholder="Address while away"
                  value={stationAddress}
                  onChange={(e) => setStationAddress(e.target.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label="Emergency Contact Number"
                  placeholder="Phone number"
                  value={contactNumber}
                  onChange={(e) => setContactNumber(e.target.value)}
                />
              </Grid.Col>
            </Grid>
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => navigate("/leave/mine")}>Cancel</Button>
            <Button type="submit" loading={submitMutation.isPending}>Submit Application</Button>
          </Group>
        </Stack>
      </form>
    </Card>
  );
}
