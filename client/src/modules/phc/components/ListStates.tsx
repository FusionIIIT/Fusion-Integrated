import { Card, Stack, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";

// The loading, error and empty states every PHC list shares.
export function ListStates({ isPending, error, empty, emptyText }: {
  isPending: boolean;
  error: unknown;
  empty: boolean;
  emptyText: string;
}) {
  if (error) return <ErrorState error={error} />;
  if (isPending) return <Text c="dimmed">Loading…</Text>;
  if (empty) {
    return (
      <Card padding="xl" withBorder>
        <Stack align="center" gap={4}><Text fw={600}>{emptyText}</Text></Stack>
      </Card>
    );
  }
  return null;
}
