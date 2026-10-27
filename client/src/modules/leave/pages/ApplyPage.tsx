import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Title,
  Paper,
  TextInput,
  Textarea,
  Select,
  Button,
  Group,
  Stack,
  Switch,
  NumberInput,
  Alert,
} from "@mantine/core";
import { leaveApi } from "../api";

export default function ApplyPage() {
  const navigate = useNavigate();
  const [category, setCategory] = useState<string>("CL");
  const today = new Date().toISOString().slice(0, 10);
  const [startDate, setStartDate] = useState<string>(today);
  const [endDate, setEndDate] = useState<string>(today);
  const [halfDaySlot, setHalfDaySlot] = useState<string>("none");
  const [reason, setReason] = useState<string>("");
  const [substituteId, setSubstituteId] = useState<number | undefined>(undefined);
  const [unitHeadId, setUnitHeadId] = useState<number | undefined>(undefined);
  const [stationLeave, setStationLeave] = useState<boolean>(false);
  const [stationAddress, setStationAddress] = useState<string>("");
  const [stationContact, setStationContact] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await leaveApi.applyLeave({
        category,
        start_date: startDate,
        end_date: endDate,
        half_day_slot: category === "CL" ? halfDaySlot : "none",
        reason,
        substitute_id: substituteId || null,
        unit_head_id: unitHeadId || null,
        station_leave_applied: stationLeave,
        station_leave_address: stationAddress,
        station_leave_contact: stationContact,
        submit_now: true,
      });
      navigate("/leave/my-leaves");
    } catch (err: any) {
      const msg = err.response?.data ? JSON.stringify(err.response.data) : "Failed to submit leave application.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="md" p="md">
      <Title order={2}>Apply for Leave</Title>
      <Paper withBorder p="lg" radius="md" maw={700}>
        <form onSubmit={handleSubmit}>
          <Stack gap="sm">
            {error && (
              <Alert color="red" title="Submission Error">
                {error}
              </Alert>
            )}

            <Select
              label="Leave Category"
              required
              value={category}
              onChange={(val) => setCategory(val || "CL")}
              data={[
                { value: "CL", label: "Casual Leave (CL)" },
                { value: "RH", label: "Restricted Holiday (RH)" },
                { value: "SCL", label: "Special Casual Leave (SCL)" },
                { value: "EL", label: "Earned Leave (EL)" },
                { value: "COL", label: "Commuted Leave (COL)" },
                { value: "VL", label: "Vacation Leave (VL)" },
              ]}
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

            {category === "CL" && startDate === endDate && (
              <Select
                label="Half-Day Slot (CL only)"
                value={halfDaySlot}
                onChange={(val) => setHalfDaySlot(val || "none")}
                data={[
                  { value: "none", label: "Full Day (1.0 day)" },
                  { value: "first_half", label: "First Half / Forenoon (0.5 day)" },
                  { value: "second_half", label: "Second Half / Afternoon (0.5 day)" },
                ]}
              />
            )}

            <Textarea
              label="Purpose / Reason"
              required
              rows={3}
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
              placeholder="State the reason for leave..."
            />

            <Group grow>
              <NumberInput
                label="Substitute Employee ID (Optional)"
                placeholder="Colleague's user ID"
                value={substituteId}
                onChange={(val) => setSubstituteId(typeof val === "number" ? val : undefined)}
              />
              <NumberInput
                label="Unit Head (HOD) ID"
                placeholder="Unit Head user ID"
                value={unitHeadId}
                onChange={(val) => setUnitHeadId(typeof val === "number" ? val : undefined)}
              />
            </Group>

            <Switch
              label="Station Leave Required (leaving Jabalpur)"
              checked={stationLeave}
              onChange={(e) => setStationLeave(e.currentTarget.checked)}
              mt="xs"
            />

            {stationLeave && (
              <Group grow>
                <TextInput
                  label="Station Leave Address"
                  required
                  placeholder="Residential / destination address"
                  value={stationAddress}
                  onChange={(e) => setStationAddress(e.currentTarget.value)}
                />
                <TextInput
                  label="Emergency Contact Number"
                  required
                  placeholder="Phone number"
                  value={stationContact}
                  onChange={(e) => setStationContact(e.currentTarget.value)}
                />
              </Group>
            )}

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/leave/my-leaves")}>
                Cancel
              </Button>
              <Button type="submit" loading={loading}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Stack>
  );
}
