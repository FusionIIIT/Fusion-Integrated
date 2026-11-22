import { useState } from "react";
import { Container, Group, Stack, Text, Title } from "@mantine/core";
import { FaScale } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances } from "../api/hooks";
import { CATEGORY_LABELS, type LeaveBalance } from "../api/types";

/** EL-UC-012: my leave account for the current year. */
export default function BalancesPage() {
  const [year, setYear] = useState(new Date().getFullYear());
  const balances = useBalances(year);

  if (balances.isError) {
    return <Container size="lg"><ErrorState error={balances.error} /></Container>;
  }

  const rows = balances.data ?? [];
  const byCategory = new Map<string, LeaveBalance>();
  for (const row of rows) byCategory.set(row.category, row);

  return (
    <Container size="lg">
      <PageHeader
        title="My Leave Balances"
        subtitle={`Year ${year}`}
        action={
          <Group gap="xs">
            <Text size="sm" c="dimmed">Year</Text>
            <select value={year} onChange={(e) => setYear(Number(e.target.value))}
                    style={{ padding: "4px 8px" }}>
              {[year - 1, year, year + 1].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </Group>
        }
      />

      {!rows.length && !balances.isPending ? (
        <Stack align="center" py={48} gap={4}>
          <FaScale size={32} color="var(--mantine-color-gray-5)" />
          <Text fw={600}>No balance recorded for {year}</Text>
          <Text c="dimmed" size="sm">
            Entitlements are credited at the year-end run, so a year with no run
            yet has nothing to show.
          </Text>
        </Stack>
      ) : (
        <Stack gap="xs">
          {Object.keys(CATEGORY_LABELS).map((category) => {
            const row = byCategory.get(category);
            return (
              <Group key={category} justify="space-between"
                     style={{ borderBottom: "1px solid var(--mantine-color-gray-2)",
                              paddingBottom: 8 }}>
                <Title order={5} fw={500}>
                  {CATEGORY_LABELS[category]}
                </Title>
                <Text fw={600} c={row && Number(row.days) <= 0 ? "red" : undefined}>
                  {row ? row.days : "—"}
                </Text>
              </Group>
            );
          })}
          <Text size="xs" c="dimmed" mt="sm">
            EL, COL and RH carry forward into the next year according to the
            current policy. Days shown are what remains, not what was granted.
          </Text>
        </Stack>
      )}
    </Container>
  );
}