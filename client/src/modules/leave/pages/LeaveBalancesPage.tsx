import { Badge, Card, SimpleGrid, Stack, Text, Title } from "@mantine/core";

import { leaveBalances } from "../data";

export default function LeaveBalancesPage() {
  return (
    <Stack gap="md">
      <Title order={2}>Leave Balances</Title>
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        {leaveBalances.map((balance) => (
          <Card key={balance.code} withBorder radius="md" p="lg">
            <Text fw={600}>{balance.label}</Text>
            <Text c="dimmed" mt="xs">
              Entitled: {balance.entitled} days
            </Text>
            <Text c="dimmed">Used: {balance.used} days</Text>
            <Text c="dimmed">Carry forward: {balance.carry_forward} days</Text>
            <Badge variant="filled" mt="md">
              Available: {balance.available} days
            </Badge>
          </Card>
        ))}
      </SimpleGrid>
    </Stack>
  );
}
