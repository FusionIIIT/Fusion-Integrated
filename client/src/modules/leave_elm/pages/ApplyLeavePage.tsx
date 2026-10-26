import React, { useState } from "react";
import {
  Card,
  Container,
  Title,
  Text,
  Select,
  TextInput,
  Textarea,
  Checkbox,
  Radio,
  Button,
  Group,
  Stack,
  Alert,
  Paper,
  Divider,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarPlus, FaInfoCircle, FaPlaneDeparture, FaUserFriends } from "react-icons/fa";

export default function ApplyLeavePage() {
  const [leaveTypeCode, setLeaveTypeCode] = useState<string>("CL");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [halfDay, setHalfDay] = useState<boolean>(false);
  const [halfDayPeriod, setHalfDayPeriod] = useState<string>("FIRST_HALF");
  const [reason, setReason] = useState<string>("");
  const [substituteUsername, setSubstituteUsername] = useState<string>("");
  const [stationLeave, setStationLeave] = useState<boolean>(false);
  const [stationAddress, setStationAddress] = useState<string>("");
  const [stationContact, setStationContact] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Dynamic duration estimate preview
  const getEstimatedDays = (): string => {
    if (!startDate || !endDate) return "0";
    if (halfDay) return "0.5";
    const d1 = new Date(startDate);
    const d2 = new Date(endDate);
    if (d1 > d2) return "Invalid date range";
    const totalDays = Math.ceil((d2.getTime() - d1.getTime()) / 86400000) + 1;
    if (["EL", "COL", "VL"].includes(leaveTypeCode)) {
      return `${totalDays} continuous days (BR-EL-011: includes weekends/holidays)`;
    }
    return `Approx. ${totalDays} working days (excluding weekends & closed holidays)`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!leaveTypeCode || !startDate || !endDate) {
      notifications.show({
        title: "Validation Error",
        message: "Please select leave type and specify valid dates.",
        color: "red",
      });
      return;
    }

    setSubmitting(true);
    const payload = {
      leave_type_code: leaveTypeCode,
      start_date: startDate,
      end_date: endDate,
      half_day: halfDay,
      half_day_period: halfDay ? halfDayPeriod : "NONE",
      reason,
      substitute_username: substituteUsername.trim() || null,
      station_leave: stationLeave,
      station_details: stationLeave
        ? { address: stationAddress, contact: stationContact }
        : null,
    };

    try {
      const response = await fetch("/api/v1/leave/applications/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (response.ok) {
        notifications.show({
          title: "Application Submitted",
          message: `Application #${data.id} created successfully! Status: ${data.status}`,
          color: "teal",
        });
        // Reset form
        setReason("");
        setSubstituteUsername("");
        setStationLeave(false);
      } else {
        notifications.show({
          title: "Submission Failed",
          message: data.error || "Could not submit application.",
          color: "red",
        });
      }
    } catch (err) {
      notifications.show({
        title: "Network Error",
        message: "Failed to connect to the leave management API.",
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="md" py="xl">
      <Card shadow="sm" padding="xl" radius="md" withBorder>
        <Group justify="space-between" mb="lg">
          <div>
            <Title order={2}>Apply for Leave</Title>
            <Text c="dimmed" size="sm">
              Submit formal leave application adhering to Fusion ELM business rules (BR-EL-001 to BR-EL-038).
            </Text>
          </div>
          <FaCalendarPlus size={32} color="#228be6" />
        </Group>

        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Category (BR-EL-001)"
              placeholder="Select leave type"
              value={leaveTypeCode}
              onChange={(val) => setLeaveTypeCode(val || "CL")}
              data={[
                { value: "CL", label: "Casual Leave (CL, 8 days/yr - Lapse at year end)" },
                { value: "RH", label: "Restricted Holiday (RH, 2 days/yr - Restricted calendar only)" },
                { value: "SCL", label: "Special Casual Leave (SCL, 15 days/yr)" },
                { value: "EL", label: "Earned Leave (EL, 30 days/yr - Continuous count, Carry forward)" },
                { value: "COL", label: "Commuted / Medical Leave (COL, 20 days/yr - Medical evidence required)" },
                { value: "VL", label: "Vacation Leave (VL, 60 days/yr - Faculty only, 2:1 EL conversion)" },
              ]}
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

            <Checkbox
              label="Half-Day Leave (Casual Leave only - BR-EL-010)"
              checked={halfDay}
              onChange={(e) => setHalfDay(e.currentTarget.checked)}
              disabled={leaveTypeCode !== "CL"}
            />

            {halfDay && (
              <Radio.Group
                label="Select Half-Day Period (BR-EL-010, BR-EL-012)"
                value={halfDayPeriod}
                onChange={setHalfDayPeriod}
              >
                <Group mt="xs">
                  <Radio value="FIRST_HALF" label="First Half (Morning Session - 0.5 day)" />
                  <Radio value="SECOND_HALF" label="Second Half (Afternoon Session - 0.5 day)" />
                </Group>
              </Radio.Group>
            )}

            <Alert icon={<FaInfoCircle size={16} />} title="Estimated Leave Duration" color="blue">
              {getEstimatedDays()}
            </Alert>

            <Textarea
              label="Reason for Leave"
              placeholder="State the academic or personal reason for absence..."
              minRows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
            />

            <Divider label="Responsibility & Travel Arrangements" labelPosition="center" />

            <TextInput
              label="Nominate Substitute / Responsibility Holder (BR-EL-014)"
              description="Another employee who will take charge of academic/administrative duties. Must not be yourself."
              placeholder="Enter substitute's Fusion username..."
              leftSection={<FaUserFriends size={14} />}
              value={substituteUsername}
              onChange={(e) => setSubstituteUsername(e.target.value)}
            />

            <Paper p="sm" withBorder radius="sm">
              <Checkbox
                label="Permission to Leave Station (Station Leave - BR-EL-013)"
                description="Check if traveling outside Jabalpur during the leave interval."
                checked={stationLeave}
                onChange={(e) => setStationLeave(e.currentTarget.checked)}
              />

              {stationLeave && (
                <Stack mt="sm" gap="xs">
                  <TextInput
                    label="Outstation Address"
                    placeholder="Residential address / Hotel / Institute address..."
                    leftSection={<FaPlaneDeparture size={14} />}
                    value={stationAddress}
                    onChange={(e) => setStationAddress(e.target.value)}
                    required={stationLeave}
                  />
                  <TextInput
                    label="Emergency Contact Phone Number"
                    placeholder="+91-XXXXXXXXXX"
                    value={stationContact}
                    onChange={(e) => setStationContact(e.target.value)}
                    required={stationLeave}
                  />
                </Stack>
              )}
            </Paper>

            <Button type="submit" size="md" color="blue" loading={submitting}>
              Submit Application
            </Button>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}