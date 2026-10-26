import { useState } from "react";
import { Badge, Card, Container, Grid, Group, Stack, Text } from "@mantine/core";
import { useLeaveBalances } from "../hooks/useLeaveRequests";
import { PageHeader } from "../../../ui/components/PageHeader";
import type { LeaveCategory } from "../api/types";

const CATEGORY_LABELS: Record<LeaveCategory, string> = {
  CL: "Casual Leave",
  RH: "Restricted Holiday",
  SCL: "Special Casual Leave",
  EL: "Earned Leave",
  VL: "Vacation Leave",
  COL: "Commuted Leave",
};

const CATEGORY_COLORS: Record<LeaveCategory, string> = {
  CL: "blue",
  RH: "orange",
  SCL: "violet",
  EL: "green",
  VL: "teal",
  COL: "red",
};

export default function LeaveBalancePage() {
  const [year, setYear] = useState(() => new Date().getFullYear());
  const { data } = useLeaveBalances(year);
  const balances = data ?? { results: [] };

  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() - i);

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balance"
        subtitle={`Leave balances for ${year}`}
        action={
          <Group>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="mantine-Input-input"
              style={{ width: 150 }}
            >
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </Group>
        }
      />
      <Grid>
        {balances.results.map((balance) => (
          <Grid.Col key={balance.id} span={6}>
            <Card padding="lg" withBorder>
              <Group justify="space-between">
                <Text fw={700} size="lg">
                  {CATEGORY_LABELS[balance.category as LeaveCategory] || balance.category}
                </Text>
                <Badge color={CATEGORY_COLORS[balance.category as LeaveCategory] || "gray"}>
                  {balance.category}
                </Badge>
              </Group>
              <Stack gap="xs" mt="md">
                <Group justify="space-between">
                  <Text>Opening</Text>
                  <Text fw={600}>{balance.opening_balance}</Text>
                </Group>
                <Group justify="space-between">
                  <Text c="green">Credited</Text>
                  <Text fw={600} c="green">+{balance.credited}</Text>
                </Group>
                <Group justify="space-between">
                  <Text c="red">Availed</Text>
                  <Text fw={600} c="red">-{balance.availed}</Text>
                </Group>
                <Group justify="space-between">
                  <Text c="orange">Lapsed</Text>
                  <Text fw={600} c="orange">-{balance.lapsed}</Text>
                </Group>
                <Group justify="space-between" style={{ borderTop: "1px solid var(--mantine-color-gray-3)", paddingTop: 8 }}>
                  <Text size="lg">Closing Balance</Text>
                  <Text size="lg" fw={700}>{balance.closing_balance}</Text>
                </Group>
              </Stack>
            </Card>
          </Grid.Col>
        ))}
      </Grid>
      {balances.results.length === 0 && (
        <Card padding="lg">
          <Text ta="center" c="dimmed">
            No leave balances found for {year}.
          </Text>
        </Card>
      )}
    </Container>
  );
}