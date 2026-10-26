import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Grid,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplyLeaveMutation, useLeaveBalances, useLeaveTypes } from "../api/hooks";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const { data: leaveTypes = [], isLoading: typesLoading } = useLeaveTypes();
  const { data: balances = [] } = useLeaveBalances();
  const applyMutation = useApplyLeaveMutation();

  const [leaveTypeId, setLeaveTypeId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [halfDayPeriod, setHalfDayPeriod] = useState<"FIRST_HALF" | "SECOND_HALF">("FIRST_HALF");
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationDestination, setStationDestination] = useState("");
  const [stationStartDate, setStationStartDate] = useState("");
  const [stationEndDate, setStationEndDate] = useState("");
  const [stationAddress, setStationAddress] = useState("");
  const [stationContactNo, setStationContactNo] = useState("");
  const [substituteId, setSubstituteId] = useState<number | "">("");

  const selectedType = leaveTypes.find((t) => String(t.id) === leaveTypeId);
  const selectedBalance = balances.find((b) => String(b.leave_type) === leaveTypeId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leaveTypeId || !startDate || !endDate || !reason.trim()) return;

    try {
      await applyMutation.mutateAsync({
        leave_type: Number(leaveTypeId),
        start_date: startDate,
        end_date: isHalfDay ? startDate : endDate,
        reason,
        is_half_day: isHalfDay,
        half_day_period: isHalfDay ? halfDayPeriod : "NONE",
        is_station_leave: isStationLeave,
        station_destination: isStationLeave ? stationDestination : "",
        station_start_date: isStationLeave ? stationStartDate || null : null,
        station_end_date: isStationLeave ? stationEndDate || null : null,
        station_address: isStationLeave ? stationAddress : "",
        station_contact_no: isStationLeave ? stationContactNo : "",
        substitute_id: substituteId ? Number(substituteId) : null,
      });
      navigate("/leave/mine");
    } catch {
      // Error handled by mutation state
    }
  };

  const typeOptions = leaveTypes.map((t) => ({
    value: String(t.id),
    label: `${t.code} — ${t.name} (Max ${t.max_days_per_year}d/yr)`,
  }));

  return (
    <div>
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new leave application with continuous counting and substitute nomination"
      />

      <form onSubmit={handleSubmit}>
        <Stack gap="lg" maw={800}>
          {applyMutation.isError && (
            <Alert color="red" title="Submission Failed">
              {(applyMutation.error as Error)?.message || "Failed to submit leave application."}
            </Alert>
          )}

          <Card withBorder padding="md" radius="sm">
            <Stack gap="md">
              <Text fw={600} size="sm">
                1. Leave Category & Available Balance
              </Text>
              <Select
                label="Leave Category"
                placeholder="Select category (CL, RH, SCL, EL, COL, VL)"
                data={typeOptions}
                value={leaveTypeId}
                onChange={setLeaveTypeId}
                disabled={typesLoading}
                required
              />

              {selectedBalance && (
                <Text size="sm" c="dimmed">
                  Available Balance:{" "}
                  <strong style={{ color: "var(--mantine-color-blue-7)" }}>
                    {selectedBalance.available} days
                  </strong>{" "}
                  (Allotted: {selectedBalance.allotted}, Used: {selectedBalance.used})
                </Text>
              )}
            </Stack>
          </Card>

          <Card withBorder padding="md" radius="sm">
            <Stack gap="md">
              <Text fw={600} size="sm">
                2. Leave Duration & Dates
              </Text>

              {selectedType?.code === "CL" && (
                <Checkbox
                  label="Half-Day Casual Leave (Consumes 0.5 day)"
                  checked={isHalfDay}
                  onChange={(e) => setIsHalfDay(e.currentTarget.checked)}
                />
              )}

              {isHalfDay && (
                <Select
                  label="Half-Day Period"
                  data={[
                    { value: "FIRST_HALF", label: "First Half (Morning)" },
                    { value: "SECOND_HALF", label: "Second Half (Afternoon)" },
                  ]}
                  value={halfDayPeriod}
                  onChange={(val) => setHalfDayPeriod((val as "FIRST_HALF" | "SECOND_HALF") || "FIRST_HALF")}
                />
              )}

              <Grid>
                <Grid.Col span={isHalfDay ? 12 : 6}>
                  <TextInput
                    label={isHalfDay ? "Date" : "Start Date"}
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.currentTarget.value)}
                    required
                  />
                </Grid.Col>
                {!isHalfDay && (
                  <Grid.Col span={6}>
                    <TextInput
                      label="End Date"
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.currentTarget.value)}
                      required
                    />
                  </Grid.Col>
                )}
              </Grid>

              <Textarea
                label="Reason / Purpose"
                placeholder="State the purpose for this leave request..."
                minRows={3}
                value={reason}
                onChange={(e) => setReason(e.currentTarget.value)}
                required
              />
            </Stack>
          </Card>

          <Card withBorder padding="md" radius="sm">
            <Stack gap="md">
              <Text fw={600} size="sm">
                3. Responsibility Coverage (Substitute Nomination)
              </Text>
              <NumberInput
                label="Nominated Substitute Employee ID"
                placeholder="Enter employee ID of the nominated colleague (optional)"
                value={substituteId}
                onChange={(val) => setSubstituteId(val === "" ? "" : Number(val))}
              />
              <Text size="xs" c="dimmed">
                Per BR-EL-014, substitute must be another employee with no overlapping leave.
              </Text>
            </Stack>
          </Card>

          <Card withBorder padding="md" radius="sm">
            <Stack gap="md">
              <Checkbox
                label="Include Station Leave (Traveling Outside Jabalpur)"
                checked={isStationLeave}
                onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
              />

              {isStationLeave && (
                <Stack gap="sm">
                  <TextInput
                    label="Station Destination"
                    placeholder="City / Country"
                    value={stationDestination}
                    onChange={(e) => setStationDestination(e.currentTarget.value)}
                    required={isStationLeave}
                  />
                  <Grid>
                    <Grid.Col span={6}>
                      <TextInput
                        label="Departure Date"
                        type="date"
                        value={stationStartDate}
                        onChange={(e) => setStationStartDate(e.currentTarget.value)}
                      />
                    </Grid.Col>
                    <Grid.Col span={6}>
                      <TextInput
                        label="Return Date"
                        type="date"
                        value={stationEndDate}
                        onChange={(e) => setStationEndDate(e.currentTarget.value)}
                      />
                    </Grid.Col>
                  </Grid>
                  <TextInput
                    label="Contact Address while Away"
                    value={stationAddress}
                    onChange={(e) => setStationAddress(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Contact Telephone / Mobile No."
                    value={stationContactNo}
                    onChange={(e) => setStationContactNo(e.currentTarget.value)}
                  />
                </Stack>
              )}
            </Stack>
          </Card>

          <Group justify="flex-end">
            <Button variant="default" onClick={() => navigate("/leave/mine")}>
              Cancel
            </Button>
            <Button type="submit" loading={applyMutation.isPending}>
              Submit Application
            </Button>
          </Group>
        </Stack>
      </form>
    </div>
  );
}
