import React, { useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { errorMessage, http } from "../../../lib/http";

const CATEGORIES = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
];

export const ApplyLeavePage: React.FC = () => {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const [category, setCategory] = useState<string>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");

  const [halfDay, setHalfDay] = useState(false);
  const [halfDayType, setHalfDayType] = useState<string>("first_half");

  const [stationLeave, setStationLeave] = useState(false);
  const [stationStart, setStationStart] = useState("");
  const [stationEnd, setStationEnd] = useState("");
  const [stationAddress, setStationAddress] = useState("");
  const [stationEmergencyContact, setStationEmergencyContact] = useState("");

  const [substituteRequired, setSubstituteRequired] = useState(false);
  const [substituteId, setSubstituteId] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate || !reason.trim()) {
      notifications.show({
        title: "Validation Error",
        message: "Please fill in start date, end date, and reason.",
        color: "red",
      });
      return;
    }

    setSubmitting(true);
    try {
      const payload: Record<string, unknown> = {
        leave_category: category,
        start_date: startDate,
        end_date: endDate,
        reason: reason.trim(),
        half_day: halfDay,
        half_day_type: halfDay ? halfDayType : "",
        station_leave: stationLeave,
        station_start_date: stationLeave ? stationStart || null : null,
        station_end_date: stationLeave ? stationEnd || null : null,
        station_address: stationLeave ? stationAddress : "",
        station_emergency_contact: stationLeave ? stationEmergencyContact : "",
        substitute_required: substituteRequired,
        substitute_id: substituteRequired && substituteId ? parseInt(substituteId, 10) : null,
      };

      await http.post("/elm/applications", payload);
      notifications.show({
        title: "Success",
        message: "Leave application submitted successfully.",
        color: "green",
      });
      navigate("/elm/applications");
    } catch (err) {
      notifications.show({
        title: "Submission Failed",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="md" py="xl">
      <Card withBorder shadow="sm" radius="md" p="xl">
        <Title order={2} mb="md">
          Apply for Leave
        </Title>
        <Text c="dimmed" size="sm" mb="lg">
          Submit a new leave application in accordance with the institute ELM policies.
        </Text>

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Category"
              data={CATEGORIES}
              value={category}
              onChange={(val) => setCategory(val || "CL")}
              required
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
              <TextInput
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </Group>

            {category === "CL" && (
              <Card withBorder p="sm" bg="gray.0">
                <Checkbox
                  label="Half Day Casual Leave (0.5 day)"
                  checked={halfDay}
                  onChange={(e) => setHalfDay(e.currentTarget.checked)}
                  mb="xs"
                />
                {halfDay && (
                  <Select
                    label="Half Day Timing"
                    data={[
                      { value: "first_half", label: "First Half (Morning)" },
                      { value: "second_half", label: "Second Half (Afternoon)" },
                    ]}
                    value={halfDayType}
                    onChange={(val) => setHalfDayType(val || "first_half")}
                  />
                )}
              </Card>
            )}

            <Card withBorder p="sm">
              <Checkbox
                label="Station Leave Permission (Leaving Jabalpur)"
                checked={stationLeave}
                onChange={(e) => setStationLeave(e.currentTarget.checked)}
                mb="xs"
              />
              {stationLeave && (
                <Stack gap="sm">
                  <Group grow>
                    <TextInput
                      label="Station Departure Date"
                      type="date"
                      value={stationStart}
                      onChange={(e) => setStationStart(e.target.value)}
                      required
                    />
                    <TextInput
                      label="Station Return Date"
                      type="date"
                      value={stationEnd}
                      onChange={(e) => setStationEnd(e.target.value)}
                      required
                    />
                  </Group>
                  <TextInput
                    label="Contact Address Outside Station"
                    value={stationAddress}
                    onChange={(e) => setStationAddress(e.target.value)}
                    required
                  />
                  <TextInput
                    label="Emergency Contact Number"
                    value={stationEmergencyContact}
                    onChange={(e) => setStationEmergencyContact(e.target.value)}
                  />
                </Stack>
              )}
            </Card>

            <Card withBorder p="sm">
              <Checkbox
                label="Nominate Substitute for Responsibility Coverage"
                checked={substituteRequired}
                onChange={(e) => setSubstituteRequired(e.currentTarget.checked)}
                mb="xs"
              />
              {substituteRequired && (
                <TextInput
                  label="Substitute Employee User ID"
                  placeholder="Enter employee ID"
                  type="number"
                  value={substituteId}
                  onChange={(e) => setSubstituteId(e.target.value)}
                  required
                />
              )}
            </Card>

            <Textarea
              label="Reason for Leave"
              placeholder="Provide justification or stated purpose"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              minRows={3}
              required
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/elm/applications")}>
                Cancel
              </Button>
              <Button type="submit" loading={submitting}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
};

export default ApplyLeavePage;
