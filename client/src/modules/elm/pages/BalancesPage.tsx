import {
  Badge, Card, Container, Group, SimpleGrid, Stack, Text, Title,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances, useElmContext } from "../api/hooks";

export default function BalancesPage() {
  const { data: balances, error, isPending } = useBalances();
  const { data: context } = useElmContext();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave Balances"
        subtitle={context
          ? `${context.designation_name ?? "Employee"} — ${context.unit?.name ?? "no unit"}`
          : undefined}
      />
      {isPending ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }}>
          {(balances ?? []).map((b) => (
            <Card key={`${b.leave_year}-${b.category}`} withBorder radius="md" p="md">
              <Group justify="space-between" mb="xs">
                <Title order={4}>{b.category}</Title>
                <Badge variant="light">{b.leave_year}</Badge>
              </Group>
              <Stack gap={4}>
                <Text>
                  Available: <b>{b.available_days}</b> day(s)
                </Text>
                <Text size="sm" c="dimmed">
                  Entitled {b.entitled_days} · carried {b.opening_days} · used{" "}
                  {b.used_days} · pending {b.pending_days}
                </Text>
              </Stack>
            </Card>
          ))}
        </SimpleGrid>
      )}
    </Container>
  );
}
