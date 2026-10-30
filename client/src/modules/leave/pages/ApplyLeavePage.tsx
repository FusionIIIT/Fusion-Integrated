import React, { useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Select,
  Stack,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);

  const [category, setCategory] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState<string | null>("full");
  const [purpose, setPurpose] = useState("");
  const [substituteId, setSubstituteId] = useState("");

  const [stationLeave, setStationLeave] = useState(false);
  const [stationStartDate, setStationStartDate] = useState("");
  const [stationEndDate, setStationEndDate] = useState("");
  const [stationAddress, setStationAddress] = useState("");
  const [stationContact, setStationContact] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!category || !startDate || !endDate || !purpose) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "Please fill in all required fields",
      });
      return;
    }

    try {
      setSubmitting(true);
      await http.post("/api/v1/leave/applications/", {
        category,
        start_date: startDate,
        end_date: endDate,
        half_day: halfDay || "full",
        purpose,
        substitute_user_id: substituteId ? parseInt(substituteId, 10) : null,
        station_leave: stationLeave,
        station_start_date: stationLeave ? stationStartDate : null,
        station_end_date: stationLeave ? stationEndDate : null,
        station_address: stationAddress,
        station_contact: stationContact,
      });

      notifications.show({
        color: "green",
        title: "Success",
        message: "Leave application submitted successfully",
      });
      navigate("/leave/dashboard");
    } catch {
      notifications.show({
        color: "red",
        title: "Error",
        message: "Failed to submit leave application",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="md" py="lg">
      <Stack gap="lg">
        <PageHeader
          title="Apply for Leave"
          description="Submit a new leave application with optional substitute and station leave"
        />

        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <form onSubmit={handleSubmit}>
            <Stack gap="md">
              <Select
                label="Leave Category"
                required
                data={[
                  { value: "CL", label: "Casual Leave (CL)" },
                  { value: "RH", label: "Restricted Holiday (RH)" },
                  { value: "SCL", label: "Special Casual Leave (SCL)" },
                  { value: "EL", label: "Earned Leave (EL)" },
                  { value: "COL", label: "Commuted Leave (COL)" },
                  { value: "VL", label: "Vacation Leave (VL)" },
                ]}
                value={category}
                onChange={setCategory}
              />

              <Group grow>
                <TextInput
                  type="date"
                  label="Start Date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
                <TextInput
                  type="date"
                  label="End Date"
                  required
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </Group>

              {category === "CL" && (
                <Select
                  label="Half Day Selection"
                  data={[
                    { value: "full", label: "Full Day" },
                    { value: "first_half", label: "First Half (0.5 day)" },
                    { value: "second_half", label: "Second Half (0.5 day)" },
                  ]}
                  value={halfDay}
                  onChange={setHalfDay}
                />
              )}

              <TextInput
                label="Nominate Substitute User ID (optional)"
                placeholder="Enter colleague's user ID"
                value={substituteId}
                onChange={(e) => setSubstituteId(e.target.value)}
              />

              <Checkbox
                label="Station Leave (outside Jabalpur travel)"
                checked={stationLeave}
                onChange={(e) => setStationLeave(e.currentTarget.checked)}
              />

              {stationLeave && (
                <Card withBorder padding="sm" radius="sm">
                  <Stack gap="xs">
                    <Title order={5}>Station Leave Details</Title>
                    <Group grow>
                      <TextInput
                        type="date"
                        label="Station Departure"
                        value={stationStartDate}
                        onChange={(e) => setStationStartDate(e.target.value)}
                      />
                      <TextInput
                        type="date"
                        label="Station Return"
                        value={stationEndDate}
                        onChange={(e) => setStationEndDate(e.target.value)}
                      />
                    </Group>
                    <TextInput
                      label="Outstation Contact Address"
                      value={stationAddress}
                      onChange={(e) => setStationAddress(e.target.value)}
                    />
                    <TextInput
                      label="Emergency Contact Phone"
                      value={stationContact}
                      onChange={(e) => setStationContact(e.target.value)}
                    />
                  </Stack>
                </Card>
              )}

              <Textarea
                label="Purpose / Reason"
                required
                rows={3}
                placeholder="State reason for leave"
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
              />

              <Group justify="flex-end" mt="md">
                <Button variant="default" onClick={() => navigate("/leave/dashboard")}>
                  Cancel
                </Button>
                <Button type="submit" loading={submitting}>
                  Submit Application
                </Button>
              </Group>
            </Stack>
          </form>
        </Card>
      </Stack>
    </Container>
  );
}
