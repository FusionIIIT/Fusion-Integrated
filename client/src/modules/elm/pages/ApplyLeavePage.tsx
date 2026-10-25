import { useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  NumberInput,
  Paper,
  Radio,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplyLeave, useLeaveBalances, useLeaveCategories } from "../api/hooks";

export default function ApplyLeavePage() {
  const navigate = useNavigate();
  const categoriesQuery = useLeaveCategories();
  const balancesQuery = useLeaveBalances();
  const applyMutation = useApplyLeave();

  const [categoryCode, setCategoryCode] = useState<string | null>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState<string>("none");
  const [reason, setReason] = useState("");

  const [stationLeave, setStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [emergencyContact, setEmergencyContact] = useState("");

  const [substituteId, setSubstituteId] = useState<number | string>("");

  if (categoriesQuery.error) {
    return (
      <Container size="md">
        <ErrorState error={categoriesQuery.error} />
      </Container>
    );
  }

  const selectedCategory = categoriesQuery.data?.find((c) => c.code === categoryCode);
  const selectedBalance = balancesQuery.data?.find(
    (b) => b.category.code === categoryCode
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryCode || !startDate || !endDate || !reason.trim()) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "Please fill all required fields.",
      });
      return;
    }

    try {
      await applyMutation.mutateAsync({
        category_code: categoryCode,
        start_date: startDate,
        end_date: endDate,
        half_day: halfDay as "none" | "first_half" | "second_half",
        reason: reason.trim(),
        station_leave: stationLeave,
        station_address: stationLeave ? stationAddress.trim() : "",
        emergency_contact: stationLeave ? emergencyContact.trim() : "",
        substitute_id: substituteId ? Number(substituteId) : null,
      });

      notifications.show({
        color: "green",
        title: "Application Submitted",
        message: "Your leave application has been submitted successfully.",
      });
      navigate("/elm/mine");
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Submission Failed",
        message: errorMessage(err),
      });
    }
  };

  const categoryOptions = (categoriesQuery.data ?? []).map((c) => ({
    value: c.code,
    label: `${c.name} (${c.code}) — Quota: ${c.annual_quota} days`,
  }));

  return (
    <Container size="md" py="xl">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new employee leave request with optional station details and substitute nomination."
      />

      <Paper withBorder p="xl" radius="md" mt="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Leave Category"
              placeholder="Select leave type"
              data={categoryOptions}
              value={categoryCode}
              onChange={setCategoryCode}
              required
            />

            {selectedCategory && (
              <Card withBorder bg="var(--mantine-color-gray-0)" p="sm" radius="sm">
                <Text size="sm" fw={500}>
                  {selectedCategory.name} Details
                </Text>
                <Text size="xs" c="dimmed">
                  {selectedCategory.description || "Official Institute Leave"}
                </Text>
                <Group mt="xs" gap="lg">
                  <Text size="xs">
                    <strong>Annual Quota:</strong> {selectedCategory.annual_quota} days
                  </Text>
                  <Text size="xs">
                    <strong>Remaining Balance:</strong>{" "}
                    {selectedBalance ? selectedBalance.balance : "—"} days
                  </Text>
                  <Text size="xs">
                    <strong>Counting:</strong>{" "}
                    {selectedCategory.continuous_counting ? "Continuous" : "Working days only"}
                  </Text>
                </Group>
              </Card>
            )}

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

            {categoryCode === "CL" && startDate === endDate && startDate && (
              <Radio.Group
                value={halfDay}
                onChange={setHalfDay}
                label="Half-Day Casual Leave"
                description="Applicable for single-day Casual Leave"
              >
                <Group mt="xs">
                  <Radio value="none" label="Full Day (1.0)" />
                  <Radio value="first_half" label="First Half (0.5)" />
                  <Radio value="second_half" label="Second Half (0.5)" />
                </Group>
              </Radio.Group>
            )}

            <Textarea
              label="Reason / Purpose"
              placeholder="Specify the reason for taking leave"
              minRows={3}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
            />

            <NumberInput
              label="Nominate Substitute Employee ID (Optional)"
              description="Leave empty if responsibility coverage is not required"
              placeholder="e.g. 2002"
              value={substituteId}
              onChange={setSubstituteId}
              min={1}
            />

            <Checkbox
              label="Station Leave Permission Required"
              description="Check if you will be leaving the headquarters during this leave period"
              checked={stationLeave}
              onChange={(e) => setStationLeave(e.currentTarget.checked)}
            />

            {stationLeave && (
              <Stack gap="sm" p="md" style={{ border: "1px dashed #ced4da", borderRadius: 8 }}>
                <Text size="sm" fw={500} c="blue">
                  Station Leave Details
                </Text>
                <TextInput
                  label="Address Outside Headquarters"
                  placeholder="Complete postal/residential address during absence"
                  value={stationAddress}
                  onChange={(e) => setStationAddress(e.target.value)}
                  required={stationLeave}
                />
                <TextInput
                  label="Emergency Contact Number"
                  placeholder="Active telephone / mobile number"
                  value={emergencyContact}
                  onChange={(e) => setEmergencyContact(e.target.value)}
                  required={stationLeave}
                />
              </Stack>
            )}

            <Group justify="flex-end" mt="lg">
              <Button variant="default" onClick={() => navigate("/elm/mine")}>
                Cancel
              </Button>
              <Button type="submit" loading={applyMutation.isPending}>
                Submit Leave Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Container>
  );
}
