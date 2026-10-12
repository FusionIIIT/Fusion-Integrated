import React, { useState } from "react";
import {
  Card,
  Title,
  TextInput,
  Select,
  Button,
  Stack,
  Text,
  Checkbox,
  Group,
  Textarea,
  Notification,
} from "@mantine/core";

export default function ApplyLeavePage() {
  const [category, setCategory] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [halfDayPeriod, setHalfDayPeriod] = useState<string | null>("first_half");
  const [reason, setReason] = useState("");
  const [leavingStation, setLeavingStation] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [emergencyPhone, setEmergencyPhone] = useState("");
  const [substituteId, setSubstituteId] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <Stack gap="lg" maw={700}>
      <Title order={2}>Apply for Leave</Title>
      <Text c="dimmed" size="sm">
        Submit a new leave application with role-based routing and substitute nomination.
      </Text>

      {submitted && (
        <Notification color="teal" title="Application Submitted" onClose={() => setSubmitted(false)}>
          Your leave application has been submitted for review.
        </Notification>
      )}

      <Card withBorder padding="lg" radius="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Category"
              placeholder="Select category"
              data={[
                { value: "CL", label: "Casual Leave (CL)" },
                { value: "RH", label: "Restricted Holiday (RH)" },
                { value: "SCL", label: "Special Casual Leave (SCL)" },
                { value: "EL", label: "Earned Leave (EL)" },
                { value: "VL", label: "Vacation Leave (VL)" },
                { value: "COL", label: "Commuted Leave (COL - Medical)" },
              ]}
              value={category}
              onChange={setCategory}
              required
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.currentTarget.value)}
                required
              />
              <TextInput
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.currentTarget.value)}
                required
              />
            </Group>

            {category === "CL" && (
              <Group>
                <Checkbox
                  label="Half Day Leave (0.5 CL)"
                  checked={isHalfDay}
                  onChange={(e) => setIsHalfDay(e.currentTarget.checked)}
                />
                {isHalfDay && (
                  <Select
                    placeholder="Select Half"
                    data={[
                      { value: "first_half", label: "First Half" },
                      { value: "second_half", label: "Second Half" },
                    ]}
                    value={halfDayPeriod}
                    onChange={setHalfDayPeriod}
                  />
                )}
              </Group>
            )}

            <Textarea
              label="Purpose / Reason"
              placeholder="State the reason for leave"
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
              minRows={3}
              required
            />

            <TextInput
              label="Substitute Employee ID (Optional)"
              placeholder="Enter User ID of nominated colleague"
              value={substituteId}
              onChange={(e) => setSubstituteId(e.currentTarget.value)}
            />

            <Checkbox
              label="Station Leave Required (Leaving Jabalpur)"
              checked={leavingStation}
              onChange={(e) => setLeavingStation(e.currentTarget.checked)}
            />

            {leavingStation && (
              <Stack gap="xs">
                <TextInput
                  label="Contact Address while on leave"
                  placeholder="Address outside station"
                  value={stationAddress}
                  onChange={(e) => setStationAddress(e.currentTarget.value)}
                />
                <TextInput
                  label="Emergency Phone"
                  placeholder="Emergency contact number"
                  value={emergencyPhone}
                  onChange={(e) => setEmergencyPhone(e.currentTarget.value)}
                />
              </Stack>
            )}

            <Button type="submit" color="blue" mt="md">
              Submit Leave Application
            </Button>
          </Stack>
        </form>
      </Card>
    </Stack>
  );
}
