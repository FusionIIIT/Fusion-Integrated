import {
  Badge,
  Card,
  Container,
  Group,
  SimpleGrid,
  Table,
  Tabs,
  Text,
} from "@mantine/core";
import { FaBook, FaCoins, FaHotel } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useBookingSummaryReport,
  useCategoryOccupancyReport,
  useInventoryUsageReport,
  useRevenueSummaryReport,
} from "../api/hooks";

export default function SupervisorReportsPage() {
  const { data: summary, error: sumError } = useBookingSummaryReport();
  const { data: catOccupancy } = useCategoryOccupancyReport();
  const { data: revenue } = useRevenueSummaryReport();
  const { data: inventoryUsage } = useInventoryUsageReport();

  if (sumError) {
    return (
      <Container size="xl">
        <ErrorState error={sumError} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel In-Charge Executive Analytics"
        subtitle="High-level metrics: booking volume, category occupancy distribution, revenue, and logistics stock."
      />

      <SimpleGrid cols={{ base: 1, sm: 4 }} mb="lg">
        <Card padding="md" withBorder>
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">
                Total Requisitions
              </Text>
              <Text fw={700} size="xl">
                {summary?.total_bookings ?? 0}
              </Text>
            </div>
            <FaBook size={24} color="#228be6" />
          </Group>
        </Card>
        <Card padding="md" withBorder>
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">
                Offline Bookings
              </Text>
              <Text fw={700} size="xl">
                {summary?.offline_bookings ?? 0}
              </Text>
            </div>
            <FaHotel size={24} color="#7950f2" />
          </Group>
        </Card>
        <Card padding="md" withBorder>
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">
                Total Billed (INR)
              </Text>
              <Text fw={700} size="xl">
                ₹{revenue?.total_billed ?? 0}
              </Text>
            </div>
            <FaCoins size={24} color="#fab005" />
          </Group>
        </Card>
        <Card padding="md" withBorder>
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">
                Settled Revenue (INR)
              </Text>
              <Text fw={700} size="xl">
                ₹{revenue?.settled_total ?? 0}
              </Text>
            </div>
            <FaCoins size={24} color="#12b886" />
          </Group>
        </Card>
      </SimpleGrid>

      <Tabs defaultValue="category">
        <Tabs.List mb="md">
          <Tabs.Tab value="category">Category-wise Occupancy</Tabs.Tab>
          <Tabs.Tab value="revenue">Financial Revenue Summary</Tabs.Tab>
          <Tabs.Tab value="inventory">Inventory Usage & Thresholds</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="category">
          <Card padding="lg" withBorder>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Visitor Category</Table.Th>
                  <Table.Th>Total Stays Completed</Table.Th>
                  <Table.Th>Total Occupants Accommodated</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {catOccupancy?.length ? (
                  catOccupancy.map((c, i) => (
                    <Table.Tr key={i}>
                      <Table.Td fw={600}>
                        <Badge color="blue">Category {c.visitor_category}</Badge>
                      </Table.Td>
                      <Table.Td>{c.total_stays}</Table.Td>
                      <Table.Td>{c.total_occupants}</Table.Td>
                    </Table.Tr>
                  ))
                ) : (
                  <Table.Tr>
                    <Table.Td colSpan={3}>
                      <Text c="dimmed">No historical category occupancy records yet.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="revenue">
          <Card padding="lg" withBorder>
            <SimpleGrid cols={{ base: 1, sm: 2 }} mb="md">
              <div>
                <Text size="sm" c="dimmed">
                  Room Rent Accrued
                </Text>
                <Text fw={700} size="lg">
                  ₹{revenue?.room_rent_total ?? 0}
                </Text>
              </div>
              <div>
                <Text size="sm" c="dimmed">
                  Mess & Dining Charges
                </Text>
                <Text fw={700} size="lg">
                  ₹{revenue?.meal_charge_total ?? 0}
                </Text>
              </div>
              <div>
                <Text size="sm" c="dimmed">
                  Cancellation Penalties Collected
                </Text>
                <Text fw={700} size="lg">
                  ₹{revenue?.cancellation_charge_total ?? 0}
                </Text>
              </div>
              <div>
                <Text size="sm" c="dimmed">
                  Total Settled Cash Inflow
                </Text>
                <Text fw={700} size="lg" c="teal">
                  ₹{revenue?.settled_total ?? 0}
                </Text>
              </div>
            </SimpleGrid>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="inventory">
          <Card padding="lg" withBorder>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Item Name</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Current Stock</Table.Th>
                  <Table.Th>Safety Threshold</Table.Th>
                  <Table.Th>Condition</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {inventoryUsage?.length ? (
                  inventoryUsage.map((item) => (
                    <Table.Tr key={item.id}>
                      <Table.Td fw={600}>{item.item_name}</Table.Td>
                      <Table.Td>{item.category}</Table.Td>
                      <Table.Td>
                        {item.current_quantity} {item.unit}
                      </Table.Td>
                      <Table.Td>
                        {item.minimum_threshold} {item.unit}
                      </Table.Td>
                      <Table.Td>
                        {item.is_below_threshold ? (
                          <Badge color="red">Below Threshold</Badge>
                        ) : (
                          <Badge color="teal">Sufficient Stock</Badge>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))
                ) : (
                  <Table.Tr>
                    <Table.Td colSpan={5}>
                      <Text c="dimmed">No inventory records available.</Text>
                    </Table.Td>
                  </Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
