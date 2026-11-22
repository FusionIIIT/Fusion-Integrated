import { Badge, Card, Container, Stack, Table, Text, Title } from "@mantine/core";
import { useGateAlerts } from "../api/hooks";

export default function SecurityAlertsPage() {
  const { data: alerts, isLoading } = useGateAlerts();

  return (
    <Container size="xl" py="md">
      <Stack gap="lg">
        <Title order={2}>Security & Gate Alerts</Title>

        {isLoading && <Text>Loading alerts...</Text>}

        <Card withBorder padding="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Severity</Table.Th>
                <Table.Th>Alert Type</Table.Th>
                <Table.Th>Details</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Logged At</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {!alerts || alerts.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={5}>
                    <Text ta="center" c="dimmed">No open security alerts.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                alerts.map((a) => (
                  <Table.Tr key={a.id}>
                    <Table.Td>
                      <Badge color={a.severity === "critical" ? "red" : a.severity === "warning" ? "orange" : "blue"}>
                        {a.severity.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{a.alert_type}</Table.Td>
                    <Table.Td>{a.message}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline">{a.status}</Badge>
                    </Table.Td>
                    <Table.Td>{new Date(a.created_at).toLocaleString()}</Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      </Stack>
    </Container>
  );
}
