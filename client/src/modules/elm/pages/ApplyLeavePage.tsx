import { useState, useMemo } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Radio,
  Select,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
  NumberInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate, Link } from "react-router-dom";
import { FaCalendarCheck, FaArrowLeft } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { elmApi } from "../api/elmApi";
import type { LeaveCategoryType, HalfDayType } from "../types";

export default function ApplyLeavePage() {
  const navigate = useNavigate();

  const [category, setCategory] = useState<LeaveCategoryType>("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [halfDay, setHalfDay] = useState<HalfDayType>("none");
  const [purpose, setPurpose] = useState("");

  // Station Leave
  const [isStationLeave, setIsStationLeave] = useState(false);
  const [stationAddress, setStationAddress] = useState("");
  const [stationContact, setStationContact] = useState("");

  // Substitute
  const [substituteId, setSubstituteId] = useState<number | string>("");

  const [submitting, setSubmitting] = useState(false);

  // Approximate duration calculation display
  const calculatedDays = useMemo(() => {
    if (!startDate || !endDate) return 0;
    if (category === "CL" && halfDay !== "none") {
      return 0.5;
    }
    const d1 = new Date(startDate);
    const d2 = new Date(endDate);
    if (d1 > d2) return 0;

    // Continuous vs working day
    if (["EL", "COL", "VL"].includes(category)) {
      const diffTime = Math.abs(d2.getTime() - d1.getTime());
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
    } else {
      let count = 0;
      const cur = new Date(d1);
      while (cur <= d2) {
        const day = cur.getDay();
        if (day !== 0 && day !== 6) count++;
        cur.setDate(cur.getDate() + 1);
      }
      return count;
    }
  }, [category, startDate, endDate, halfDay]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate) {
      notifications.show({
        title: "Validation Error",
        message: "Start and End dates are required.",
        color: "red",
      });
      return;
    }
    if (!purpose.trim()) {
      notifications.show({
        title: "Validation Error",
        message: "Please provide a reason or purpose for the leave.",
        color: "red",
      });
      return;
    }

    setSubmitting(true);
    try {
      await elmApi.applyLeave({
        category,
        start_date: startDate,
        end_date: endDate,
        purpose,
        half_day: category === "CL" ? halfDay : "none",
        is_station_leave: isStationLeave,
        station_address: isStationLeave ? stationAddress : "",
        station_contact: isStationLeave ? stationContact : "",
        substitute_user_id: substituteId ? Number(substituteId) : null,
      });

      notifications.show({
        title: "Success",
        message: "Leave application submitted successfully.",
        color: "green",
      });
      navigate("/elm/mine");
    } catch (err: unknown) {
      notifications.show({
        title: "Submission Error",
        message: err instanceof Error ? err.message : "Failed to apply for leave.",
        color: "red",
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="md" py="lg">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new employee leave application with complete validations."
        action={
          <Button component={Link} to="/elm/mine" variant="default" leftSection={<FaArrowLeft />}>
            Back to My Leaves
          </Button>
        }
      />

      <form onSubmit={handleSubmit}>
        <Stack gap="lg">
          <Card withBorder radius="md">
            <Title order={4} mb="md">
              Leave Details
            </Title>
            <Stack gap="md">
              <Select
                label="Leave Category"
                required
                data={[
                  { value: "CL", label: "Casual Leave (CL) - 8 days/year" },
                  { value: "RH", label: "Restricted Holiday (RH) - 2 days/year" },
                  { value: "SCL", label: "Special Casual Leave (SCL) - up to 15 days/year" },
                  { value: "EL", label: "Earned Leave (EL) - 30 days/year (Non-Faculty)" },
                  { value: "COL", label: "Commuted Leave (COL) - 20 days/year" },
                  { value: "VL", label: "Vacation Leave (VL) - 60 days (Faculty Only)" },
                ]}
                value={category}
                onChange={(val) => {
                  if (val) setCategory(val as LeaveCategoryType);
                }}
              />

              <Group grow>
                <TextInput
                  type="date"
                  label="Start Date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.currentTarget.value)}
                />
                <TextInput
                  type="date"
                  label="End Date"
                  required
                  value={endDate}
                  onChange={(e) => setEndDate(e.currentTarget.value)}
                />
              </Group>

              {category === "CL" && (
                <Radio.Group
                  label="Casual Leave Duration"
                  value={halfDay}
                  onChange={(val) => setHalfDay(val as HalfDayType)}
                >
                  <Group mt="xs">
                    <Radio value="none" label="Full Day" />
                    <Radio value="first_half" label="First Half Day (0.5d)" />
                    <Radio value="second_half" label="Second Half Day (0.5d)" />
                  </Group>
                </Radio.Group>
              )}

              {/* Calculated duration banner */}
              <Alert icon={<FaCalendarCheck />} color="blue" title="Duration Calculation">
                Requested duration: <strong>{calculatedDays} day(s)</strong>.
                {["EL", "COL", "VL"].includes(category) ? (
                  <Text size="xs" mt={2}>
                    (Continuous counting: includes intervening weekends and closed holidays per rule BR-EL-011)
                  </Text>
                ) : (
                  <Text size="xs" mt={2}>
                    (Excludes weekends and closed holidays per rule BR-EL-011)
                  </Text>
                )}
              </Alert>

              <Textarea
                label="Purpose / Reason for Leave"
                placeholder="State the reason for this leave request"
                required
                minRows={3}
                value={purpose}
                onChange={(e) => setPurpose(e.currentTarget.value)}
              />
            </Stack>
          </Card>

          {/* Station Leave Section */}
          <Card withBorder radius="md">
            <Title order={4} mb="xs">
              Station Leave Permission
            </Title>
            <Text size="xs" c="dimmed" mb="md">
              (BR-EL-013: Station Leave permission is coupled directly inside the same leave application.)
            </Text>
            <Stack gap="md">
              <Checkbox
                label="Will you be travelling outside Jabalpur during this leave period?"
                checked={isStationLeave}
                onChange={(e) => setIsStationLeave(e.currentTarget.checked)}
              />

              {isStationLeave && (
                <Stack gap="sm">
                  <TextInput
                    label="Out of Station Address"
                    placeholder="Address during absence from headquarters"
                    required={isStationLeave}
                    value={stationAddress}
                    onChange={(e) => setStationAddress(e.currentTarget.value)}
                  />
                  <TextInput
                    label="Emergency Contact Number"
                    placeholder="Mobile / telephone number"
                    required={isStationLeave}
                    value={stationContact}
                    onChange={(e) => setStationContact(e.currentTarget.value)}
                  />
                </Stack>
              )}
            </Stack>
          </Card>

          {/* Substitute Coverage Section */}
          <Card withBorder radius="md">
            <Title order={4} mb="xs">
              Substitute Coverage Nomination
            </Title>
            <Text size="xs" c="dimmed" mb="md">
              (BR-EL-014, BR-EL-015: Exactly one eligible employee nominated; approval routing waits for consent.)
            </Text>
            <Stack gap="md">
              <NumberInput
                label="Nominated Substitute Employee ID (optional)"
                placeholder="Enter IAM User ID of another employee"
                value={substituteId}
                onChange={(val) => setSubstituteId(val)}
                min={1}
              />
              <Text size="xs" c="dimmed">
                If provided, the substitute will receive a notification and must accept responsibility before
                the application proceeds to the Unit Head.
              </Text>
            </Stack>
          </Card>

          <Group justify="flex-end">
            <Button component={Link} to="/elm/mine" variant="default">
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Submit Leave Application
            </Button>
          </Group>
        </Stack>
      </form>
    </Container>
  );
}
