import {
  Badge,
  Card,
  Container,
  Group,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";

const leaveRecords = [
  { id: "L-2041", type: "Casual Leave", dates: "2026-10-18 to 2026-10-19", status: "Approved", days: 2 },
  { id: "L-2045", type: "Earned Leave", dates: "2026-11-08 to 2026-11-12", status: "Pending", days: 5 },
  { id: "L-2049", type: "Restricted Holiday", dates: "2026-12-03", status: "Rejected", days: 1 },
];

const statusColor: Record<string, string> = {
  Approved: "green",
  Pending: "yellow",
  Rejected: "red",
};

export default function MyLeavesPage() {
  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <Group justify="space-between">
          <div>
            <Title order={2}>My Leave</Title>
            <Text c="dimmed" size="sm">
              Track all submitted and historical leave balances.
            </Text>
          </div>
          <Badge variant="light" color="blue" size="lg">3 records</Badge>
        </Group>

        <SimpleGrid cols={{ base: 1, md: 2 }}>
          {leaveRecords.map((record) => (
            <Card key={record.id} withBorder radius="md" padding="lg">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Text fw={600}>{record.type}</Text>
                  <Badge color={statusColor[record.status] ?? "gray"} variant="light">
                    {record.status}
                  </Badge>
                </Group>

                <Text size="sm" c="dimmed">{record.id}</Text>
                <Text>{record.dates}</Text>
                <Text size="sm">Duration: {record.days} day{record.days === 1 ? "" : "s"}</Text>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      </Stack>
    </Container>
  );
}
