import { useState } from "react";
import {
  Badge,
  Card,
  Container,
  Grid,
  Group,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
} from "@mantine/core";
import { FaCalendarCheck, FaInfoCircle } from "react-icons/fa";


import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyBalances } from "../api/hooks";
import type { LeaveBalance } from "../api/types";

const CATEGORY_INFO: Record<string, { name: string; max?: number; description: string; color: string }> = {
  CL: {
    name: "Casual Leave",
    max: 8,
    description: "8 days per year. Non-accumulative (lapses at year end). Half-day allowed.",
    color: "blue",
  },
  RH: {
    name: "Restricted Holiday",
    max: 2,
    description: "2 days per year from published festival list. Non-accumulative.",
    color: "violet",
  },
  SCL: {
    name: "Special Casual Leave",
    max: 15,
    description: "Up to 15 days per year for academic/official conferences. Lapses at year end.",
    color: "teal",
  },
  EL: {
    name: "Earned Leave",
    max: 300,
    description: "30 days/yr for non-faculty. Carries forward up to 300 days accumulation limit.",
    color: "green",
  },
  COL: {
    name: "Commuted Leave",
    max: 20,
    description: "20 days per year against medical certificate. Maximum balance 20 days.",
    color: "orange",
  },
  VL: {
    name: "Vacation Leave",
    max: 60,
    description: "60 days/yr for faculty. Unused days convert to EL at 2:1 ratio at year end.",
    color: "pink",
  },
};

export default function LeaveBalancePage() {
  const currentYear = new Date().getFullYear();
  const [selectedYear, setSelectedYear] = useState<string>(String(currentYear));

  const { data, isPending, error } = useMyBalances(Number(selectedYear));

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const balances = (data?.results ?? []) as LeaveBalance[];

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balances"
        subtitle={`Current entitlements and balances for calendar year ${selectedYear}`}
        action={
          <Select
            data={[
              { value: String(currentYear - 1), label: String(currentYear - 1) },
              { value: String(currentYear), label: String(currentYear) },
              { value: String(currentYear + 1), label: String(currentYear + 1) },
            ]}
            value={selectedYear}
            onChange={(val) => setSelectedYear(val || String(currentYear))}
            w={120}
          />
        }
      />

      <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
        {balances.map((b) => {
          const info = CATEGORY_INFO[b.category] || {
            name: b.category,
            max: 30,
            description: "",
            color: "gray",
          };
          const totalEntitled = Number(b.credited) + Number(b.carried_forward);
          const usedNum = Number(b.used);
          const percentUsed = totalEntitled > 0 ? Math.min(100, Math.round((usedNum / totalEntitled) * 100)) : 0;

          return (
            <Card key={b.id} padding="lg" radius="md" withBorder>
              <Stack gap="sm">
                <Group justify="space-between">
                  <Group gap="xs">
                    <ThemeIcon color={info.color} size="lg" radius="md">
                      <FaCalendarCheck />
                    </ThemeIcon>
                    <div>
                      <Text fw={700} size="md">
                        {b.category}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {info.name}
                      </Text>
                    </div>
                  </Group>
                  <Badge color={info.color} variant="light" size="lg">
                    {b.available} Available
                  </Badge>
                </Group>

                <Progress value={percentUsed} color={info.color} size="sm" radius="xl" mt="xs" />

                <Grid mt="xs">
                  <Grid.Col span={4}>
                    <Text size="xs" c="dimmed">
                      Credited
                    </Text>
                    <Text fw={600} size="sm">
                      {b.credited}
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={4}>
                    <Text size="xs" c="dimmed">
                      Carried
                    </Text>
                    <Text fw={600} size="sm">
                      {b.carried_forward}
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={4}>
                    <Text size="xs" c="dimmed">
                      Used
                    </Text>
                    <Text fw={600} size="sm" c="red">
                      {b.used}
                    </Text>
                  </Grid.Col>
                </Grid>

                <Text size="xs" c="dimmed" mt="xs">
                  {info.description}
                </Text>
              </Stack>
            </Card>
          );
        })}
      </SimpleGrid>

      {balances.length === 0 && !isPending && (
        <Card padding="xl" radius="md" withBorder mt="lg">
          <Group justify="center" gap="md">
            <FaInfoCircle size={24} color="gray" />
            <Text c="dimmed">No leave balances found for year {selectedYear}.</Text>
          </Group>
        </Card>
      )}
    </Container>
  );
}
