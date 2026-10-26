import { useState } from "react";
import { Badge, Card, Grid, Group, NumberInput, Progress, Stack, Text, ThemeIcon } from "@mantine/core";
import { FaCalendarCheck } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances } from "../api/hooks";

export default function LeaveBalancesPage() {
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState<number>(currentYear);
  const { data: balances = [], isLoading } = useLeaveBalances(selectedYear);

  return (
    <div>
      <PageHeader
        title="Leave Balances"
        subtitle="Annual entitlements, accumulated balances, and year-end carry forward status"
        action={
          <Group gap="xs">
            <Text size="sm">Year:</Text>
            <NumberInput
              w={100}
              value={selectedYear}
              onChange={(val) => setSelectedYear(Number(val) || currentYear)}
              min={2020}
              max={2035}
            />
          </Group>
        }
      />

      <Grid>
        {balances.map((b) => {
          const usedPct = b.allotted > 0 ? Math.min(100, Math.round((b.used / b.allotted) * 100)) : 0;
          return (
            <Grid.Col key={b.id} span={{ base: 12, sm: 6, md: 4 }}>
              <Card withBorder padding="lg" radius="md">
                <Stack gap="sm">
                  <Group justify="space-between">
                    <Group gap="xs">
                      <ThemeIcon size="lg" radius="md" variant="light" color="blue">
                        <FaCalendarCheck size={16} />
                      </ThemeIcon>
                      <div>
                        <Text fw={600} size="md">
                          {b.leave_type_code}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {b.leave_type_name}
                        </Text>
                      </div>
                    </Group>
                    <Badge size="lg" variant="light" color={b.available > 0 ? "teal" : "red"}>
                      {b.available}d left
                    </Badge>
                  </Group>

                  <Progress value={usedPct} color={usedPct > 80 ? "red" : "blue"} size="sm" mt="xs" />

                  <Group justify="space-between" mt="xs">
                    <div>
                      <Text size="xs" c="dimmed">Allotted</Text>
                      <Text fw={500} size="sm">{b.allotted} days</Text>
                    </div>
                    <div>
                      <Text size="xs" c="dimmed">Used</Text>
                      <Text fw={500} size="sm">{b.used} days</Text>
                    </div>
                    <div>
                      <Text size="xs" c="dimmed">Available</Text>
                      <Text fw={600} size="sm" c="blue">{b.available} days</Text>
                    </div>
                  </Group>

                  {b.credited_from_vl > 0 && (
                    <Text size="xs" c="teal" mt={4}>
                      Includes {b.credited_from_vl}d converted from Vacation Leave (2:1 ratio)
                    </Text>
                  )}
                </Stack>
              </Card>
            </Grid.Col>
          );
        })}
      </Grid>
    </div>
  );
}
