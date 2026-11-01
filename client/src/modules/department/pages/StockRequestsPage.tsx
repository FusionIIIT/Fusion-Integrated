import { useState } from "react";
import { Card, Container, Stack, Text } from "@mantine/core";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useStockRequests } from "../api/hooks";

export default function StockRequestsPage() {
  const { data, isPending, error } = useStockRequests();
  const [loading] = useState(isPending);

  if (error) return <Container size="md"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  return (
    <Container size="md">
      <PageHeader title="Stock Requests" />

      {loading && <Text c="dimmed">Loading…</Text>}

      {!loading && rows.length === 0 && (
        <Card padding="xl">
          <Stack align="center" gap={6}>
            <Text fw={600}>No stock requests found</Text>
          </Stack>
        </Card>
      )}

      <Stack gap="md">
        {rows.map((request) => (
          <Card
            key={request.id} padding="lg" withBorder
          >
            <Stack gap="sm">
              <Text fw={700}>{request.item}</Text>
              <Text>Quantity: {request.quantity}</Text>
              <Text>State: {request.state}</Text>
            </Stack>
          </Card>
        ))}
      </Stack>
    </Container>
  );
}
