import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBalances } from "../api/hooks";
import type { LeaveBalance } from "../api/types";

export default function BalancesPage() {
  const [lookupUserId, setLookupUserId] = useState<number | undefined>(undefined);
  const [queryUserId, setQueryUserId] = useState<number | undefined>(undefined);

  const { data: balances, isPending, error } = useBalances(queryUserId);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setQueryUserId(lookupUserId);
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Balances"
        subtitle="Institute leave balances directory and ledger overview"
      />

      <Stack gap="lg">
        <Card padding="md" withBorder>
          <form onSubmit={handleSearch}>
            <Group align="flex-end">
              <NumberInput
                label="Filter by Employee User ID"
                placeholder="Enter User ID (or leave blank for own)"
                value={lookupUserId}
                onChange={(val) => setLookupUserId(typeof val === "number" ? val : undefined)}
                style={{ flex: 1 }}
              />
              <Button type="submit" loading={isPending}>View Balances</Button>
              {queryUserId && (
                <Button
                  variant="subtle"
                  onClick={() => {
                    setLookupUserId(undefined);
                    setQueryUserId(undefined);
                  }}
                >
                  Reset
                </Button>
              )}
            </Group>
          </form>
        </Card>

        <div>
          <Title order={4} mb="sm">
            {queryUserId ? `Balances for Employee #${queryUserId}` : "Active Balances"}
          </Title>
          <SimpleGrid cols={{ base: 2, sm: 3, md: 4, lg: 6 }} spacing="sm">
            {(balances ?? []).map((b: LeaveBalance) => (
              <Card key={b.category} padding="md" withBorder>
                <Text size="xs" c="dimmed" fw={700}>{b.category}</Text>
                <Text size="2xl" fw={700} c="blue">{b.available}</Text>
                <Text size="xs" c="dimmed">Credited: {b.credited}</Text>
                <Text size="xs" c="dimmed">Consumed: {b.consumed}</Text>
                <Text size="xs" c="dimmed">Restored: {b.restored}</Text>
              </Card>
            ))}
          </SimpleGrid>
        </div>
      </Stack>
    </Container>
  );
}
