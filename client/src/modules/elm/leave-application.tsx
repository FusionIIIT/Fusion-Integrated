import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Divider,
  Group,
  Paper,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

const LEAVE_TYPES = [
  { value: "annual", label: "Annual leave" },
  { value: "sick", label: "Sick leave" },
  { value: "casual", label: "Casual leave" },
  { value: "personal", label: "Personal leave" },
  { value: "marriage", label: "Marriage leave" },
];

export default function LeaveApplicationPage() {
  const [leaveType, setLeaveType] = useState<string | null>("annual");
  const [startDate, setStartDate] = useState("2026-11-01");
  const [endDate, setEndDate] = useState("2026-11-05");
  const [reason, setReason] = useState("Family travel and rest for the week.");

  const totalDays = useMemo(() => {
    if (!startDate || !endDate) return 0;
    const start = new Date(startDate);
    const end = new Date(endDate);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return 0;
    const ms = Math.max(0, end.getTime() - start.getTime());
    return Math.floor(ms / (1000 * 60 * 60 * 24)) + 1;
  }, [startDate, endDate]);

  const handleSubmit = () => {
    if (!leaveType || !startDate || !endDate || !reason.trim()) {
      notifications.show({
        color: "red",
        title: "Incomplete application",
        message: "Please complete all leave details before submitting.",
      });
      return;
    }

    notifications.show({
      color: "green",
      title: "Leave submitted",
      message: `Your ${LEAVE_TYPES.find((t) => t.value === leaveType)?.label ?? "leave"} request for ${totalDays} day(s) has been saved for review.`,
    });
  };

  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <div>
          <Text size="sm" tt="uppercase" c="blue" fw={700}>ELM</Text>
          <Text fz="2rem" fw={700}>Apply for leave</Text>
          <Text c="dimmed" size="sm">
            Submit a leave request, review balances, and track approvals in one place.
          </Text>
        </div>

        <Paper withBorder radius="md" p="lg">
          <Group justify="space-between" align="center" mb="md">
            <Stack gap={0}>
              <Text fw={700}>Available balance</Text>
              <Text size="sm" c="dimmed">This academic year</Text>
            </Stack>
            <Badge size="lg" variant="light" color="green">12 days remaining</Badge>
          </Group>

          <Group grow>
            <Card withBorder p="md">
              <Text c="dimmed" size="xs" tt="uppercase">Annual</Text>
              <Text fw={700} fz="lg">14 days</Text>
            </Card>
            <Card withBorder p="md">
              <Text c="dimmed" size="xs" tt="uppercase">Sick</Text>
              <Text fw={700} fz="lg">7 days</Text>
            </Card>
            <Card withBorder p="md">
              <Text c="dimmed" size="xs" tt="uppercase">Casual</Text>
              <Text fw={700} fz="lg">3 days</Text>
            </Card>
          </Group>
        </Paper>

        <Card withBorder radius="md" p="lg">
          <Stack gap="lg">
            <Group justify="space-between" align="center">
              <Text fw={700} fz="lg">Leave details</Text>
              <Badge variant="light" color="blue">Draft</Badge>
            </Group>

            <Select
              label="Leave type"
              data={LEAVE_TYPES}
              value={leaveType}
              onChange={setLeaveType}
              placeholder="Choose leave type"
              required
            />

            <Group grow>
              <TextInput
                label="Start date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.currentTarget.value)}
                required
              />
              <TextInput
                label="End date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.currentTarget.value)}
                required
              />
            </Group>

            <Paper bg="var(--mantine-color-gray-0)" p="sm" radius="sm">
              <Text size="sm" c="dimmed">Requested duration</Text>
              <Text fw={700} fz="lg">{totalDays} day(s)</Text>
            </Paper>

            <Textarea
              label="Reason for leave"
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
              minRows={4}
              autosize
              required
            />

            <Divider />

            <Group justify="flex-end">
              <Button variant="default">Save draft</Button>
              <Button onClick={handleSubmit}>Submit application</Button>
            </Group>
          </Stack>
        </Card>
      </Stack>
    </Container>
  );
}
