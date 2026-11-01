import {
  Card,
  Container,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { FaAward, FaChartLine, FaCoins, FaFolderOpen } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePortfolioAnalytics } from "../api/hooks";

export default function AnalyticsPage() {
  const { data, isPending, error } = usePortfolioAnalytics();

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Portfolio Analytics & IP Intelligence"
        subtitle="Institutional intellectual property analytics, filing velocity trends, domain clustering, and budget utilization."
      />

      {error && <ErrorState error={error} />}

      {isPending && <Text size="sm" c="dimmed">Loading portfolio intelligence metrics…</Text>}

      {data && (
        <Stack gap="lg">
          <SimpleGrid cols={{ base: 1, sm: 4 }}>
            <Paper p="md" withBorder>
              <Group>
                <FaFolderOpen size={28} color="#228be6" />
                <div>
                  <Text size="xs" c="dimmed" fw={700}>
                    TOTAL DISCLOSURES
                  </Text>
                  <Text fw={700} size="xl">
                    {data.total_applications}
                  </Text>
                </div>
              </Group>
            </Paper>

            <Paper p="md" withBorder>
              <Group>
                <FaChartLine size={28} color="#fd7e14" />
                <div>
                  <Text size="xs" c="dimmed" fw={700}>
                    ACTIVE PROSECUTION
                  </Text>
                  <Text fw={700} size="xl">
                    {data.active_patents}
                  </Text>
                </div>
              </Group>
            </Paper>

            <Paper p="md" withBorder>
              <Group>
                <FaAward size={28} color="#12b886" />
                <div>
                  <Text size="xs" c="dimmed" fw={700}>
                    PATENTS GRANTED
                  </Text>
                  <Text fw={700} size="xl">
                    {data.granted_patents}
                  </Text>
                </div>
              </Group>
            </Paper>

            <Paper p="md" withBorder>
              <Group>
                <FaCoins size={28} color="#fab005" />
                <div>
                  <Text size="xs" c="dimmed" fw={700}>
                    BUDGET ALLOCATED
                  </Text>
                  <Text fw={700} size="xl">
                    ₹ {data.budget_summary.total_allocated}
                  </Text>
                </div>
              </Group>
            </Paper>
          </SimpleGrid>

          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <Card withBorder p="md">
              <Text fw={700} size="md" mb="md">
                Distribution by Technical Domain
              </Text>
              <Table withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Domain</Table.Th>
                    <Table.Th style={{ width: 100, textAlign: "right" }}>Count</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {Object.entries(data.by_domain || {}).map(([domain, count]) => (
                    <Table.Tr key={domain}>
                      <Table.Td>{domain}</Table.Td>
                      <Table.Td style={{ textAlign: "right", fontWeight: 600 }}>{count}</Table.Td>
                    </Table.Tr>
                  ))}
                  {!Object.keys(data.by_domain || {}).length && (
                    <Table.Tr>
                      <Table.Td colSpan={2} style={{ textAlign: "center", color: "#868e96" }}>
                        No domain distributions recorded.
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Card>

            <Card withBorder p="md">
              <Text fw={700} size="md" mb="md">
                Filing Trends by Calendar Year
              </Text>
              <Table withTableBorder>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Calendar Year</Table.Th>
                    <Table.Th style={{ width: 100, textAlign: "right" }}>Filings</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {data.filing_trends?.map((item) => (
                    <Table.Tr key={item.year}>
                      <Table.Td>CY {item.year}</Table.Td>
                      <Table.Td style={{ textAlign: "right", fontWeight: 600 }}>{item.count}</Table.Td>
                    </Table.Tr>
                  ))}
                  {!data.filing_trends?.length && (
                    <Table.Tr>
                      <Table.Td colSpan={2} style={{ textAlign: "center", color: "#868e96" }}>
                        No annual trends recorded.
                      </Table.Td>
                    </Table.Tr>
                  )}
                </Table.Tbody>
              </Table>
            </Card>
          </SimpleGrid>
        </Stack>
      )}
    </Container>
  );
}
