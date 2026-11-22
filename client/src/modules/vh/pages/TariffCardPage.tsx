import { Badge, Card, Container, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useTariffs } from "../api/hooks";
import type { TariffConfig } from "../api/types";

export default function TariffCardPage() {
  const { data: tariffs, isPending, error } = useTariffs();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Hostel Tariff Schedule"
        subtitle="Official room tariff matrix approved by institute competent authority."
      />

      <Card padding="lg" withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Visitor Category</Table.Th>
              <Table.Th>Room Type</Table.Th>
              <Table.Th>Occupancy</Table.Th>
              <Table.Th>Daily Rate (INR)</Table.Th>
              <Table.Th>Effective From</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isPending ? (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text ta="center" py="md">Loading tariffs...</Text>
                </Table.Td>
              </Table.Tr>
            ) : tariffs?.length ? (
              tariffs.map((t: TariffConfig) => (
                <Table.Tr key={t.id}>
                  <Table.Td>
                    <Badge color="blue">Category {t.category}</Badge>
                  </Table.Td>
                  <Table.Td>{t.room_type === "suite" ? "Suite (AC)" : "Standard (Non-Suite)"}</Table.Td>
                  <Table.Td style={{ textTransform: "capitalize" }}>{t.occupancy}</Table.Td>
                  <Table.Td>
                    <Text fw={600}>₹{t.daily_rate}</Text>
                  </Table.Td>
                  <Table.Td>{t.effective_from}</Table.Td>
                  <Table.Td>
                    <Badge color={t.is_active ? "teal" : "gray"}>
                      {t.is_active ? "Active" : "Archived"}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))
            ) : (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text ta="center" py="md" c="dimmed">
                    No tariff records found.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
