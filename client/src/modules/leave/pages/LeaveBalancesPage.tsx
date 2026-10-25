import { Card, Container, Group, Stack, Text, Title } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances } from "../api/hooks";
import type { LeaveBalance } from "../api/types";

export default function LeaveBalancesPage() {
  const { data, isPending, error } = useLeaveBalances();

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  return (
    <Container size="lg">
      <PageHeader title="Leave Balances" subtitle="Your leave balance per category." />
      <Group gap="md" wrap="wrap">
        {(data ?? []).map((b: LeaveBalance) => (
          <Card key={b.id} padding="lg" radius="md" withBorder style={{ minWidth: 220 }}>
            <Stack gap={4}>
              <Title order={4}>{b.leave_type_code}</Title>
              <Text size="sm" c="dimmed">{b.leave_type_name}</Text>
              <Text size="xl" fw={700}>{b.remaining_days}</Text>
              <Text size="xs" c="dimmed">remaining of {b.allocated_days} (used {b.used_days})</Text>
            </Stack>
          </Card>
        ))}
        {!isPending && (data ?? []).length === 0 && <Text c="dimmed">No balances allocated yet.</Text>}
      </Group>
    </Container>
  );
}