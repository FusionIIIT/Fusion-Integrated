import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Grid,
  Group,
  Radio,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaCheckCircle, FaInfoCircle, FaMapMarkerAlt, FaUserFriends } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances, useLeaveTypes, useSubmitLeaveApplication } from "../api/hooks";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const { data: leaveTypes, isPending: typesLoading } = useLeaveTypes();
  const { data: balances } = useLeaveBalances();
  const submitMutation = useSubmitLeaveApplication();

  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [halfDayPeriod, setHalfDayPeriod] = useState<string>("FIRST_HALF");
  const [substituteId, setSubstituteId] = useState("");
  const [stationLeaveRequired, setStationLeaveRequired] = useState(false);
  const [departureDate, setDepartureDate] = useState("");
  const [arrivalDate, setArrivalDate] = useState("");
  const [stationAddress, setStationAddress] = useState("");
  const [emergencyContact, setEmergencyContact] = useState("");

  const selectedType = useMemo(
    () => leaveTypes?.find((t) => String(t.id) === selectedTypeId),
    [leaveTypes, selectedTypeId]
  );

  const selectedBalance = useMemo(
    () => balances?.find((b) => b.leave_type === Number(selectedTypeId)),
    [balances, selectedTypeId]
  );

  const typeOptions = useMemo(
    () =>
      (leaveTypes ?? []).map((t) => ({
        value: String(t.id),
        label: `${t.name} (${t.code})`,
      })),
    [leaveTypes]
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedTypeId || !startDate || !endDate || !reason.trim()) {
      notifications.show({
        color: "red",
        title: "Required Fields Missing",
        message: "Please fill in leave category, start date, end date, and reason.",
      });
      return;
    }

    submitMutation.mutate(
      {
        leave_type: Number(selectedTypeId),
        start_date: startDate,
        end_date: endDate,
        reason: reason.trim(),
        is_half_day: isHalfDay,
        half_day_period: isHalfDay ? halfDayPeriod : "",
        substitute_id: substituteId.trim(),
        station_leave_required: stationLeaveRequired,
        departure_date: stationLeaveRequired ? departureDate || null : null,
        arrival_date: stationLeaveRequired ? arrivalDate || null : null,
        station_address: stationLeaveRequired ? stationAddress.trim() : "",
        emergency_contact: stationLeaveRequired ? emergencyContact.trim() : "",
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Application Submitted",
            message: "Your leave application has been submitted successfully.",
            icon: <FaCheckCircle />,
          });
          navigate("/leave/applications");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Submission Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a leave application with entitlement verification and coverage routing"
      />

      <Stack gap="lg">
        {balances && balances.length > 0 && (
          <Card withBorder padding="md" radius="md">
            <Text fw={600} size="sm" mb="xs" c="dimmed">
              Your Current Leave Balances
            </Text>
            <Group gap="xs" wrap="wrap">
              {balances.map((b) => (
                <Badge
                  key={b.id}
                  size="lg"
                  variant={b.leave_type === Number(selectedTypeId) ? "filled" : "light"}
                  color="blue"
                >
                  {b.leave_type_code}: {b.available} days left
                </Badge>
              ))}
            </Group>
          </Card>
        )}

        <form onSubmit={handleSubmit}>
          <Card withBorder shadow="sm" radius="md" padding="xl">
            <Stack gap="md">
              <Select
                label="Leave Category"
                placeholder="Choose category (CL, RH, SCL, EL, COL, VL)"
                data={typeOptions}
                value={selectedTypeId}
                onChange={setSelectedTypeId}
                disabled={typesLoading}
                required
              />

              {selectedType && (
                <Alert icon={<FaInfoCircle />} color="blue" variant="light">
                  <Text size="sm">
                    <strong>{selectedType.name}:</strong> {selectedType.description}
                  </Text>
                  {selectedBalance && (
                    <Text size="xs" mt="4px">
                      Available balance: <strong>{selectedBalance.available} days</strong> (Credited: {selectedBalance.credited}, Consumed: {selectedBalance.consumed})
                    </Text>
                  )}
                </Alert>
              )}

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
                    value={endDate}
                    onChange={(e) => setEndDate(e.currentTarget.value)}
                    required
                  />
                </Grid.Col>
              </Grid>

              {selectedType?.code === "CL" && (
                <Card withBorder padding="sm" radius="sm">
                  <Checkbox
                    label="Apply as Half-Day Casual Leave (0.5 day)"
                    checked={isHalfDay}
                    onChange={(e) => setIsHalfDay(e.currentTarget.checked)}
                  />
                  {isHalfDay && (
                    <Radio.Group
                      value={halfDayPeriod}
                      onChange={setHalfDayPeriod}
                      label="Half-Day Period"
                      mt="xs"
                    >
                      <Group mt="xs">
                        <Radio value="FIRST_HALF" label="First Half (Morning Session)" />
                        <Radio value="SECOND_HALF" label="Second Half (Afternoon Session)" />
                      </Group>
                    </Radio.Group>
                  )}
                </Card>
              )}

              <TextInput
                label="Nominated Substitute Employee ID / Username"
                placeholder="e.g. faculty_user or staff_user"
                description={
                  selectedType?.requires_substitute
                    ? "Required: The substitute must consent before Unit Head approval routing begins."
                    : "Optional for this leave category."
                }
                value={substituteId}
                onChange={(e) => setSubstituteId(e.currentTarget.value)}
                leftSection={<FaUserFriends />}
              />

              <Textarea
                label="Reason / Purpose of Leave"
                placeholder="State the purpose for taking leave..."
                value={reason}
                onChange={(e) => setReason(e.currentTarget.value)}
                minRows={3}
                required
              />

              <Card withBorder padding="md" radius="sm">
                <Checkbox
                  label="Station Leave Permission Required (Leaving Campus / Station)"
                  checked={stationLeaveRequired}
                  onChange={(e) => setStationLeaveRequired(e.currentTarget.checked)}
                />

                {stationLeaveRequired && (
                  <Stack gap="sm" mt="md">
                    <Grid>
                      <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput
                          label="Departure Date"
                          type="date"
                          value={departureDate}
                          onChange={(e) => setDepartureDate(e.currentTarget.value)}
                          required={stationLeaveRequired}
                        />
                      </Grid.Col>
                      <Grid.Col span={{ base: 12, sm: 6 }}>
                        <TextInput
                          label="Arrival Date"
                          type="date"
                          value={arrivalDate}
                          onChange={(e) => setArrivalDate(e.currentTarget.value)}
                          required={stationLeaveRequired}
                        />
                      </Grid.Col>
                    </Grid>
                    <TextInput
                      label="Destination Address during Station Leave"
                      placeholder="Outstation address or travel destination"
                      leftSection={<FaMapMarkerAlt />}
                      value={stationAddress}
                      onChange={(e) => setStationAddress(e.currentTarget.value)}
                      required={stationLeaveRequired}
                    />
                    <TextInput
                      label="Emergency Contact Phone"
                      placeholder="+91 9876543210"
                      value={emergencyContact}
                      onChange={(e) => setEmergencyContact(e.currentTarget.value)}
                      required={stationLeaveRequired}
                    />
                  </Stack>
                )}
              </Card>

              <Group justify="flex-end" mt="md">
                <Button variant="default" onClick={() => navigate("/leave/applications")}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={submitMutation.isPending}
                  leftSection={<FaCalendarAlt />}
                >
                  Submit Application
                </Button>
              </Group>
            </Stack>
          </Card>
        </form>
      </Stack>
    </Container>
  );
}
