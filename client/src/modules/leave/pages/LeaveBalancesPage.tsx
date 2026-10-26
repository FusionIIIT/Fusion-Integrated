import {
  Badge,
  Card,
  Center,
  Container,
  Group,
  Loader,
  Progress,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyBalances } from "../api";
import type { LeaveBalance } from "../types";

const TYPE_NAMES: Record<string, string> = {
  casual: "Casual Leave (CL)",
  restricted: "Restricted Holiday (RH)",
  medical: "Medical Leave (ML)",
  earned: "Earned Leave (EL)",
  vacation: "Vacation Leave (VL)",
  sabbatical: "Sabbatical Leave (SL)",
};

export default function LeaveBalancesPage() {
  const { data: balances, isPending, error } = useMyBalances();

  if (isPending) {
    return (
      <Container size="xl">
        <Center py="xl">
          <Loader size="md" />
        </Center>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const items = balances || [];

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balances"
        subtitle="Current annual leave quotas and available balance breakdown (BR-HR-008 / BR-HR-010)"
      />

      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="lg">
        {items.map((bal: LeaveBalance) => {
          const total = Number(bal.total_entitlement) || 1;
          const consumed = Number(bal.consumed_days) || 0;
          const available = Number(bal.available_balance) || 0;
          const pct = Math.min(100, Math.round((consumed / total) * 100));

          return (
            <Card key={bal.id} padding="lg" radius="md" withBorder shadow="sm">
              <Stack gap="md">
                <Group justify="space-between" align="flex-start">
                  <div>
                    <Text fw={700} size="md">
                      {TYPE_NAMES[bal.leave_type] || bal.leave_type}
                    </Text>
                    <Text size="xs" c="dimmed">
                      Year {bal.year} Entitlement
                    </Text>
                  </div>
                  <Badge color="blue" variant="light" size="lg">
                    {available} left
                  </Badge>
                </Group>

                <div>
                  <Group justify="space-between" mb={4}>
                    <Text size="xs" c="dimmed">
                      Consumed: {consumed} days
                    </Text>
                    <Text size="xs" fw={500}>
                      Quota: {total} days
                    </Text>
                  </Group>
                  <Progress value={pct} color={pct > 80 ? "red" : pct > 50 ? "yellow" : "teal"} size="sm" radius="xl" />
                </div>
              </Stack>
            </Card>
          );
        })}
      </SimpleGrid>
    </Container>
  );
}
