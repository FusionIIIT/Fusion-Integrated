import React, { useEffect, useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Grid,
  Group,
  Select,
  Stack,
  TextInput,
  Textarea,
  Title,
  Text,
  Alert,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { leaveApi, type LeaveType } from "../api/leaveApi";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const [types, setTypes] = useState<LeaveType[]>([]);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [halfDaySlot, setHalfDaySlot] = useState<string | null>("FORENOON");
  const [reason, setReason] = useState("");

  // Station Leave
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationStartDate, setStationStartDate] = useState("");
  const [stationEndDate, setStationEndDate] = useState("");
  const [stationAddress, setStationAddress] = useState("");
  const [emergencyContact, setEmergencyContact] = useState("");

  // Attachment
  const [attachmentPath, setAttachmentPath] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    leaveApi.getLeaveTypes().then(setTypes).catch(console.error);
  }, []);

  const selectedType = types.find((t) => String(t.id) === selectedTypeId);

  const calculateDuration = () => {
    if (isHalfDay) return 0.5;
    if (!startDate || !endDate) return 0;
    const s = new Date(startDate);
    const e = new Date(endDate);
    const diff = (e.getTime() - s.getTime()) / (1000 * 3600 * 24) + 1;
    return diff > 0 ? diff : 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setSuccessMessage(null);

    if (!selectedTypeId) {
      setErrorMessage("Please select a leave category.");
      return;
    }

    const duration = calculateDuration();
    if (duration <= 0) {
      setErrorMessage("End date must be on or after start date.");
      return;
    }

    setSubmitting(true);
    try {
      await leaveApi.submitLeaveRequest({
        leave_type: Number(selectedTypeId),
        start_date: startDate,
        end_date: isHalfDay ? startDate : endDate,
        duration_days: duration,
        is_half_day: isHalfDay,
        half_day_slot: isHalfDay ? (halfDaySlot || undefined) : undefined,
        reason,
        is_station_leave: isStationLeave,
        station_start_date: isStationLeave ? stationStartDate : undefined,
        station_end_date: isStationLeave ? stationEndDate : undefined,
        station_address: isStationLeave ? stationAddress : undefined,
        emergency_contact_no: isStationLeave ? emergencyContact : undefined,
        attachment_path: attachmentPath || undefined,
      });

      setSuccessMessage("Leave application submitted successfully!");
      setTimeout(() => navigate("/leave/history"), 1200);
    } catch (err: any) {
      setErrorMessage(err.message || "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="md" py="xl">
      <Title order={2} mb="lg">
        Apply for Leave
      </Title>

      {errorMessage && (
        <Alert color="red" mb="md" title="Submission Error">
          {errorMessage}
        </Alert>
      )}

      {successMessage && (
        <Alert color="teal" mb="md" title="Success">
          {successMessage}
        </Alert>
      )}

      <Card withBorder radius="md" p="xl" component="form" onSubmit={handleSubmit}>
        <Stack gap="md">
          <Select
            label="Leave Category"
            placeholder="Select leave type"
            data={types.map((t) => ({ value: String(t.id), label: `${t.code} - ${t.name}` }))}
            value={selectedTypeId}
            onChange={setSelectedTypeId}
            required
          />

          <Grid>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.currentTarget.value)}
                required
              />
            </Grid.Col>
            <Grid.Col span={{ base: 12, sm: 6 }}>
              <TextInput
                label="End Date"
                type="date"
                value={isHalfDay ? startDate : endDate}
                disabled={isHalfDay}
                onChange={(e) => setEndDate(e.currentTarget.value)}
                required={!isHalfDay}
              />
            </Grid.Col>
          </Grid>

          {selectedType?.allows_half_day && (
            <Group>
              <Checkbox
                label="Half Day Leave (CL only)"
                checked={isHalfDay}
                onChange={(e) => setIsHalfDay(e.currentTarget.checked)}
              />
              {isHalfDay && (
                <Select
                  data={[
                    { value: "FORENOON", label: "Forenoon (First Half)" },
                    { value: "AFTERNOON", label: "Afternoon (Second Half)" },
                  ]}
                  value={halfDaySlot}
                  onChange={setHalfDaySlot}
                />
              )}
            </Group>
          )}

          <Text size="sm" fw={500} c="dimmed">
            Calculated Duration: {calculateDuration()} day(s)
          </Text>

          <Textarea
            label="Reason for Leave"
            placeholder="Provide brief justification..."
            minRows={3}
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            required
          />

          {/* Station Leave Section */}
          <Card withBorder bg="gray.0" p="md">
            <Checkbox
              label="Station Leave Permission (Requires leaving Jabalpur)"
              checked={isStationLeave}
              onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
              mb={isStationLeave ? "md" : 0}
            />

            {isStationLeave && (
              <Stack gap="sm">
                <Grid>
                  <Grid.Col span={6}>
                    <TextInput
                      label="Station Start Date"
                      type="date"
                      value={stationStartDate}
                      onChange={(e) => setStationStartDate(e.currentTarget.value)}
                      required={isStationLeave}
                    />
                  </Grid.Col>
                  <Grid.Col span={6}>
                    <TextInput
                      label="Station End Date"
                      type="date"
                      value={stationEndDate}
                      onChange={(e) => setStationEndDate(e.currentTarget.value)}
                      required={isStationLeave}
                    />
                  </Grid.Col>
                </Grid>
                <TextInput
                  label="Outstation Contact Address"
                  placeholder="Address outside Jabalpur"
                  value={stationAddress}
                  onChange={(e) => setStationAddress(e.currentTarget.value)}
                  required={isStationLeave}
                />
                <TextInput
                  label="Emergency Contact Phone"
                  placeholder="Phone number reachable during leave"
                  value={emergencyContact}
                  onChange={(e) => setEmergencyContact(e.currentTarget.value)}
                  required={isStationLeave}
                />
              </Stack>
            )}
          </Card>

          {/* Attachment for COL/Medical */}
          {selectedType?.requires_attachment && (
            <TextInput
              label="Medical Certificate / Supporting Document"
              placeholder="Certificate URL or filename"
              value={attachmentPath}
              onChange={(e) => setAttachmentPath(e.currentTarget.value)}
              required
            />
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => navigate("/leave/balances")}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Submit Application
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
