import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  LoadingOverlay,
  Select,
  Stack,
  TextInput,
  Textarea,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateLeaveRequest } from "../api";
import type { LeaveCategory } from "../types";

export default function LeaveRequestForm() {
  const navigate = useNavigate();
  const createMutation = useCreateLeaveRequest();

  const [category, setCategory] = useState<string | null>("cl");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState(false);
  const [halfDayType, setHalfDayType] = useState<string | null>("first_half");
  const [reason, setReason] = useState("");

  // Station Leave (BR-EL-013)
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [stationStartDate, setStationStartDate] = useState("");
  const [stationEndDate, setStationEndDate] = useState("");

  // Substitute (BR-EL-014, BR-EL-015)
  const [substituteId, setSubstituteId] = useState("");

  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!category) {
      setFormError("Please select a leave category.");
      return;
    }

    if (!startDate || !endDate) {
      setFormError("Start and end dates are required.");
      return;
    }

    if (new Date(startDate) > new Date(endDate)) {
      setFormError("End date cannot be earlier than start date.");
      return;
    }

    // Half-day rules (BR-EL-010)
    if (halfDay) {
      if (category !== "cl") {
        setFormError("Half-day leave is only permitted for Casual Leave (CL) (BR-EL-010).");
        return;
      }
      if (startDate !== endDate) {
        setFormError("Half-day leave must be on a single date (start date must equal end date).");
        return;
      }
      if (!halfDayType) {
        setFormError("Please select First Half or Second Half.");
        return;
      }
    }

    // Station leave rules (BR-EL-013)
    if (isStationLeave && !stationAddress.trim()) {
      setFormError("Station address is required when station leave is requested (BR-EL-013).");
      return;
    }

    const payload: any = {
      category: category as LeaveCategory,
      start_date: startDate,
      end_date: endDate,
      half_day: halfDay,
      half_day_type: halfDay ? halfDayType : null,
      reason,
      is_station_leave: isStationLeave,
      station_address: isStationLeave ? stationAddress : "",
      station_start_date: isStationLeave && stationStartDate ? stationStartDate : null,
      station_end_date: isStationLeave && stationEndDate ? stationEndDate : null,
      substitute_id: substituteId.trim() ? parseInt(substituteId, 10) : null,
    };

    try {
      await createMutation.mutateAsync(payload);
      notifications.show({
        title: "Leave Application Submitted",
        message: "Your leave request has been submitted successfully.",
        color: "teal",
      });
      navigate("/elm/leave-requests");
    } catch (err: any) {
      const errDetail = err.response?.data?.detail || err.response?.data?.error || "Failed to submit request.";
      setFormError(typeof errDetail === "string" ? errDetail : JSON.stringify(errDetail));
      notifications.show({
        title: "Submission Failed",
        message: typeof errDetail === "string" ? errDetail : "Validation failed.",
        color: "red",
      });
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new employee leave application (EL-UC-001)"
      />
      <Card padding="lg" withBorder radius="md" pos="relative">
        <LoadingOverlay visible={createMutation.isPending} />

        {formError && (
          <Alert color="red" title="Validation Error" mb="md" withCloseButton onClose={() => setFormError(null)}>
            {formError}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Category"
              placeholder="Select category"
              data={[
                { value: "cl", label: "Casual Leave (CL) — 8 days/yr" },
                { value: "rh", label: "Restricted Holiday (RH) — 2 days/yr" },
                { value: "scl", label: "Special Casual Leave (SCL) — up to 15 days/yr" },
                { value: "el", label: "Earned Leave (EL)" },
                { value: "col", label: "Commuted Leave (COL) — medical" },
                { value: "vl", label: "Faculty Vacation Leave (VL) — 60 days/yr" },
              ]}
              value={category}
              onChange={(val) => {
                setCategory(val);
                if (val !== "cl") setHalfDay(false);
              }}
              required
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => {
                  setStartDate(e.target.value);
                  if (halfDay) setEndDate(e.target.value);
                }}
                required
              />
              <TextInput
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                disabled={halfDay}
                required
              />
            </Group>

            {/* Half-Day CL Option (BR-EL-010) */}
            {category === "cl" && (
              <Card withBorder padding="sm" bg="var(--mantine-color-blue-0)">
                <Group justify="space-between">
                  <div>
                    <Checkbox
                      label="Half-Day Leave (0.5 day)"
                      description="Available exclusively for Casual Leave (CL)"
                      checked={halfDay}
                      onChange={(e) => {
                        const checked = e.currentTarget.checked;
                        setHalfDay(checked);
                        if (checked && startDate) setEndDate(startDate);
                      }}
                    />
                  </div>
                  {halfDay && (
                    <Select
                      label="Session"
                      data={[
                        { value: "first_half", label: "First Half (Morning)" },
                        { value: "second_half", label: "Second Half (Afternoon)" },
                      ]}
                      value={halfDayType}
                      onChange={setHalfDayType}
                      size="xs"
                      w={180}
                      required
                    />
                  )}
                </Group>
              </Card>
            )}

            {/* Substitute Gate (BR-EL-014, BR-EL-015) */}
            <TextInput
              label="Nominate Substitute User ID (Optional)"
              description="Nominate an eligible colleague to cover responsibilities during leave"
              placeholder="e.g. 1002"
              type="number"
              value={substituteId}
              onChange={(e) => setSubstituteId(e.target.value)}
            />

            {/* Station Leave Coupling (BR-EL-013) */}
            <Card withBorder padding="sm">
              <Checkbox
                label="Station Leave Permission Required"
                description="Check if traveling outside the institute headquarters during this period"
                checked={isStationLeave}
                onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
                mb={isStationLeave ? "sm" : 0}
              />
              {isStationLeave && (
                <Stack gap="xs" mt="xs">
                  <Textarea
                    label="Station Address & Contact Details"
                    placeholder="Provide destination address and emergency telephone number"
                    value={stationAddress}
                    onChange={(e) => setStationAddress(e.target.value)}
                    required
                  />
                  <Group grow>
                    <TextInput
                      label="Station Departure Date"
                      type="date"
                      value={stationStartDate}
                      onChange={(e) => setStationStartDate(e.target.value)}
                    />
                    <TextInput
                      label="Station Return Date"
                      type="date"
                      value={stationEndDate}
                      onChange={(e) => setStationEndDate(e.target.value)}
                    />
                  </Group>
                </Stack>
              )}
            </Card>

            <Textarea
              label="Reason / Purpose of Leave"
              placeholder="State the detailed reason for applying for leave"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
              required
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" component={Link} to="/elm/leave-requests">
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
