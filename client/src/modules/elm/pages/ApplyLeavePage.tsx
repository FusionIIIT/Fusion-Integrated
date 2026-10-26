import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";

const leaveOptions = [
  { value: "CL", label: "Casual Leave" },
  { value: "RH", label: "Restricted Holiday" },
  { value: "SCL", label: "Special Casual Leave" },
  { value: "EL", label: "Earned Leave" },
  { value: "COL", label: "Compensatory Leave" },
  { value: "VL", label: "Vacation Leave" },
] as const;

const balanceByType: Record<string, number> = {
  CL: 8,
  RH: 2,
  SCL: 5,
  EL: 10,
  COL: 3,
  VL: 12,
};

function countDays(startDate: string, endDate: string): number {
  if (!startDate || !endDate) return 0;
  const start = new Date(`${startDate}T00:00:00`);
  const end = new Date(`${endDate}T00:00:00`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) {
    return 0;
  }
  const diffMs = end.getTime() - start.getTime();
  return Math.max(1, Math.floor(diffMs / (1000 * 60 * 60 * 24)) + 1);
}

export default function ApplyLeavePage() {
  const [leaveType, setLeaveType] = useState("CL");
  const [startDate, setStartDate] = useState("2026-10-20");
  const [endDate, setEndDate] = useState("2026-10-21");
  const [reason, setReason] = useState("Family travel and personal commitments.");
  const [substitute, setSubstitute] = useState("Aisha Verma");
  const [isHalfDay, setIsHalfDay] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const totalDays = useMemo(() => {
    const days = countDays(startDate, endDate);
    return isHalfDay ? Math.max(days / 2, 0.5) : days;
  }, [endDate, isHalfDay, startDate]);

  const balance = Math.max((balanceByType[leaveType] ?? 0) - totalDays, 0);

  const handleSubmit = () => {
    setSubmitted(true);
  };

  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <Group justify="space-between" align="flex-end">
          <div>
            <Title order={2}>Apply Leave</Title>
            <Text c="dimmed" size="sm">
              Submit a leave request for approval.
            </Text>
          </div>
          <Badge variant="light" color="blue" size="lg">
            {totalDays} day{totalDays === 1 ? "" : "s"}
          </Badge>
        </Group>

        <SimpleGrid cols={{ base: 1, md: 2 }}>
          <Card withBorder radius="md" padding="lg">
            <Stack gap="md">
              <Select
                label="Leave type"
                data={leaveOptions}
                value={leaveType}
                onChange={(value) => setLeaveType(value ?? "CL")}
              />

              <Group grow>
                <TextInput
                  label="Start date"
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.currentTarget.value)}
                />
                <TextInput
                  label="End date"
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.currentTarget.value)}
                />
              </Group>

              <Textarea
                label="Reason"
                minRows={4}
                value={reason}
                onChange={(event) => setReason(event.currentTarget.value)}
              />

              <TextInput
                label="Substitute"
                value={substitute}
                onChange={(event) => setSubstitute(event.currentTarget.value)}
              />

              <Checkbox
                label="Half-day leave"
                checked={isHalfDay}
                onChange={(event) => setIsHalfDay(event.currentTarget.checked)}
              />

              <Group justify="space-between">
                <Button variant="default">Save draft</Button>
                <Button onClick={handleSubmit}>Submit request</Button>
              </Group>
            </Stack>
          </Card>

          <Card withBorder radius="md" padding="lg">
            <Stack gap="md">
              <Title order={4}>Request summary</Title>
              <Text>
                Requested leave: <strong>{totalDays} day{totalDays === 1 ? "" : "s"}</strong>
              </Text>
              <Text>
                Available balance: <strong>{balanceByType[leaveType] ?? 0} day(s)</strong>
              </Text>
              <Text>
                Remaining after request: <strong>{balance} day(s)</strong>
              </Text>
              <Text size="sm" c="dimmed">
                Most departments require the substitute to be confirmed before approval.
              </Text>
            </Stack>
          </Card>
        </SimpleGrid>

        {submitted && (
          <Card withBorder radius="md" padding="lg" bg="green.0">
            <Text fw={600} c="green.8">Leave request submitted</Text>
            <Text size="sm" c="green.8">
              Your {leaveOptions.find((item) => item.value === leaveType)?.label ?? "leave"} request
              for {totalDays} day{totalDays === 1 ? "" : "s"} has been queued for approval.
            </Text>
          </Card>
        )}
      </Stack>
    </Container>
  );
}
