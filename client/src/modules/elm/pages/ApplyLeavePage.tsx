import { useState } from "react";
import {
  Card,
  Title,
  Text,
  Select,
  TextInput,
  Textarea,
  Checkbox,
  Button,
  Stack,
  Group,
  Alert,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { applyLeave } from "../api";
import { errorMessage } from "../../../lib/http";

export default function ApplyLeavePage() {
  const navigate = useNavigate();

  const [leaveType, setLeaveType] = useState<string>("CL");
  const [startDate, setStartDate] = useState<string>("");
  const [startHalf, setStartHalf] = useState<string>("FULL");
  const [endDate, setEndDate] = useState<string>("");
  const [endHalf, setEndHalf] = useState<string>("FULL");
  const [reason, setReason] = useState<string>("");

  // Station Leave
  const [stationLeave, setStationLeave] = useState<boolean>(false);
  const [stationAddress, setStationAddress] = useState<string>("");
  const [stationContact, setStationContact] = useState<string>("");
  const [emergencyContact, setEmergencyContact] = useState<string>("");

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!startDate || !endDate) {
      setError("Please select both start and end dates.");
      return;
    }
    if (!reason.trim()) {
      setError("Please provide a reason for your leave request.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await applyLeave({
        leave_type: leaveType,
        start_date: startDate,
        start_half: startHalf,
        end_date: endDate,
        end_half: endHalf,
        reason,
        station_leave: stationLeave,
        station_address: stationAddress,
        station_contact: stationContact,
        emergency_contact: emergencyContact,
      });
      navigate("/elm/history");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Stack gap="lg" p="md" maw={700} mx="auto">
      <div>
        <Title order={2}>Apply for Leave</Title>
        <Text c="dimmed">Submit a new leave application with optional station leave details</Text>
      </div>

      {error && (
        <Alert color="red" title="Error" withCloseButton onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card withBorder shadow="sm" radius="md" p="xl" component="form" onSubmit={handleSubmit}>
        <Stack gap="md">
          <Select
            label="Leave Category"
            required
            value={leaveType}
            onChange={(val) => setLeaveType(val || "CL")}
            data={[
              { value: "CL", label: "Casual Leave (CL)" },
              { value: "RH", label: "Restricted Holiday (RH)" },
              { value: "SCL", label: "Special Casual Leave (SCL)" },
              { value: "EL", label: "Earned Leave (EL)" },
              { value: "VL", label: "Vacation Leave (VL)" },
              { value: "COL", label: "Commuted / Medical Leave (COL)" },
            ]}
          />

          <Group grow>
            <TextInput
              label="Start Date"
              type="date"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
            {leaveType === "CL" && (
              <Select
                label="Start Session"
                value={startHalf}
                onChange={(val) => setStartHalf(val || "FULL")}
                data={[
                  { value: "FULL", label: "Full Day" },
                  { value: "FIRST_HALF", label: "First Half (0.5)" },
                  { value: "SECOND_HALF", label: "Second Half (0.5)" },
                ]}
              />
            )}
          </Group>

          <Group grow>
            <TextInput
              label="End Date"
              type="date"
              required
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
            {leaveType === "CL" && (
              <Select
                label="End Session"
                value={endHalf}
                onChange={(val) => setEndHalf(val || "FULL")}
                data={[
                  { value: "FULL", label: "Full Day" },
                  { value: "FIRST_HALF", label: "First Half (0.5)" },
                  { value: "SECOND_HALF", label: "Second Half (0.5)" },
                ]}
              />
            )}
          </Group>

          <Textarea
            label="Reason / Purpose"
            required
            minRows={3}
            placeholder="Explain the purpose of your leave..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />

          <Checkbox
            label="Require Station Leave (Traveling outside Jabalpur during leave interval)"
            checked={stationLeave}
            onChange={(e) => setStationLeave(e.currentTarget.checked)}
            mt="xs"
          />

          {stationLeave && (
            <Card withBorder bg="gray.0" radius="sm" p="md">
              <Stack gap="sm">
                <Text fw={600} size="sm">
                  Station Leave Details
                </Text>
                <TextInput
                  label="Address during leave"
                  required={stationLeave}
                  placeholder="Full contact address while out of station"
                  value={stationAddress}
                  onChange={(e) => setStationAddress(e.target.value)}
                />
                <Group grow>
                  <TextInput
                    label="Station Contact Number"
                    placeholder="Phone number"
                    value={stationContact}
                    onChange={(e) => setStationContact(e.target.value)}
                  />
                  <TextInput
                    label="Emergency Contact Number"
                    placeholder="Emergency contact"
                    value={emergencyContact}
                    onChange={(e) => setEmergencyContact(e.target.value)}
                  />
                </Group>
              </Stack>
            </Card>
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => navigate("/elm/dashboard")}>
              Cancel
            </Button>
            <Button type="submit" loading={loading} color="blue">
              Submit Application
            </Button>
          </Group>
        </Stack>
      </Card>
    </Stack>
  );
}
