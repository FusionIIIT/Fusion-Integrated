import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Grid,
  Group,
  Select,
  Stack,
  Switch,
  TextInput,
  Textarea,
  Title,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { leaveApi } from "../api/client";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const [category, setCategory] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDayType, setHalfDayType] = useState<string | null>("full");
  const [purpose, setPurpose] = useState("");
  const [substituteUserId, setSubstituteUserId] = useState<string>("");
  const [responsibilities, setResponsibilities] = useState("");
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationDestination, setStationDestination] = useState("");
  const [addressDuringLeave, setAddressDuringLeave] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!category || !startDate || !endDate || !purpose.trim()) {
      notifications.show({
        title: "Validation Error",
        message: "Please fill in all required fields (Category, Dates, Purpose).",
        color: "red",
      });
      return;
    }

    try {
      setLoading(true);
      await leaveApi.applyForLeave({
        category,
        start_date: startDate,
        end_date: endDate,
        half_day_type: halfDayType ?? "full",
        purpose: purpose.trim(),
        substitute_user_id: substituteUserId ? parseInt(substituteUserId, 10) : null,
        responsibilities: responsibilities.trim(),
        is_station_leave: isStationLeave,
        station_destination: stationDestination.trim(),
        address_during_leave: addressDuringLeave.trim(),
      });

      notifications.show({
        title: "Success",
        message: "Leave application submitted successfully.",
        color: "teal",
      });
      navigate("/leave/mine");
    } catch (err) {
      notifications.show({
        title: "Application Failed",
        message: errorMessage(err),
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new employee leave request with automatic calendar and balance validation."
      />

      <Card padding="xl" shadow="sm" radius="md" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Title order={4}>Leave Details</Title>
            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <Select
                  label="Leave Category"
                  placeholder="Select category"
                  data={[
                    { value: "CL", label: "Casual Leave (CL)" },
                    { value: "RH", label: "Restricted Holiday (RH)" },
                    { value: "SCL", label: "Special Casual Leave (SCL)" },
                    { value: "EL", label: "Earned Leave (EL)" },
                    { value: "VL", label: "Vacation Leave (VL - Faculty)" },
                    { value: "COL", label: "Commuted Leave (COL)" },
                  ]}
                  value={category}
                  onChange={setCategory}
                  required
                />
              </Grid.Col>
              {category === "CL" && (
                <Grid.Col span={{ base: 12, sm: 6 }}>
                  <Select
                    label="Half-Day Option"
                    data={[
                      { value: "full", label: "Full Day (1.0)" },
                      { value: "first_half", label: "First Half (0.5)" },
                      { value: "second_half", label: "Second Half (0.5)" },
                    ]}
                    value={halfDayType}
                    onChange={setHalfDayType}
                  />
                </Grid.Col>
              )}
            </Grid>

            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="Start Date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="date"
                  label="End Date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.currentTarget.value)}
                  required
                />
              </Grid.Col>
            </Grid>

            <Textarea
              label="Purpose / Reason"
              placeholder="State the reason for leave..."
              value={purpose}
              onChange={(e) => setPurpose(e.currentTarget.value)}
              minRows={3}
              required
            />

            <Title order={4} mt="sm">Substitute / Responsibility Coverage</Title>
            <Text size="xs" c="dimmed">
              Optionally nominate another employee to carry responsibility during your absence.
            </Text>
            <Grid>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  type="number"
                  label="Substitute Employee User ID"
                  placeholder="e.g. 102"
                  value={substituteUserId}
                  onChange={(e) => setSubstituteUserId(e.currentTarget.value)}
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6 }}>
                <TextInput
                  label="Assigned Responsibilities"
                  placeholder="e.g. Lectures, lab supervision"
                  value={responsibilities}
                  onChange={(e) => setResponsibilities(e.currentTarget.value)}
                />
              </Grid.Col>
            </Grid>

            <Title order={4} mt="sm">Station Leave & Contact Details</Title>
            <Switch
              label="Permission required to leave station (leave campus / city)"
              checked={isStationLeave}
              onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
            />
            {isStationLeave && (
              <TextInput
                label="Station Destination"
                placeholder="e.g. Delhi, Mumbai"
                value={stationDestination}
                onChange={(e) => setStationDestination(e.currentTarget.value)}
                required={isStationLeave}
              />
            )}

            <TextInput
              label="Address / Contact during leave"
              placeholder="Contact number or temporary address"
              value={addressDuringLeave}
              onChange={(e) => setAddressDuringLeave(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="lg">
              <Button variant="default" onClick={() => navigate("/leave/mine")}>
                Cancel
              </Button>
              <Button type="submit" loading={loading}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
