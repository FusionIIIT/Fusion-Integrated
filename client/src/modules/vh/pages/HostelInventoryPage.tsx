import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { useState } from "react";
import {
  FaBoxes,
  FaExclamationCircle,
  FaExclamationTriangle,
  FaPlus,
  FaSync,
} from "react-icons/fa";

import {
  useInventoryAlerts,
  useInventoryItems,
  useReplenishments,
  useRequestReplenishment,
} from "../api/hooks";
import type { InventoryItem } from "../api/types";

export default function HostelInventoryPage() {
  const { data: items, isLoading: loadingItems, refetch: refetchItems } = useInventoryItems();
  const { refetch: refetchAlerts } = useInventoryAlerts();
  const { data: replenishments, isLoading: loadingReplenishments, refetch: refetchReplenishments } = useReplenishments();

  const requestReplenishment = useRequestReplenishment();

  const [activeTab, setActiveTab] = useState<string | null>("stock");

  // Replenishment Request Modal state
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);
  const [requestModalOpen, setRequestModalOpen] = useState(false);
  const [requestQty, setRequestQty] = useState<number | string>(10);
  const [requestRemarks, setRequestRemarks] = useState("");

  const handleOpenRequest = (item: InventoryItem) => {
    setSelectedItem(item);
    setRequestQty(Math.max(1, item.minimum_threshold - item.current_quantity + 5));
    setRequestRemarks(`Threshold replenishment for ${item.name}`);
    setRequestModalOpen(true);
  };

  const handleConfirmRequest = async () => {
    if (!selectedItem) return;
    await requestReplenishment.mutateAsync({
      itemId: selectedItem.id,
      quantity: Number(requestQty),
      remarks: requestRemarks,
    });
    setRequestModalOpen(false);
    setSelectedItem(null);
  };

  const itemsBelowThreshold = (items || []).filter((i) => i.is_below_threshold);
  const pendingRequests = (replenishments || []).filter((r) => r.status === "PENDING");

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case "LINEN":
        return "blue";
      case "UTENSILS":
        return "indigo";
      case "CONSUMABLES":
        return "teal";
      default:
        return "gray";
    }
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="lg">
        {/* Header */}
        <Group justify="space-between" align="flex-start">
          <div>
            <Title order={2}>Visitors Hostel Inventory & Stock</Title>
            <Text c="dimmed" size="sm">
              Stock auditing, minimum threshold monitoring, and automated replenishment requests (UC-VH-009, BR-VH-009)
            </Text>
          </div>
          <Button
            variant="default"
            onClick={() => {
              refetchItems();
              refetchAlerts();
              refetchReplenishments();
            }}
            leftSection={<FaSync />}
          >
            Refresh
          </Button>
        </Group>

        {/* Overview Stats */}
        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Total Tracked Items
                </Text>
                <Title order={3}>{(items || []).length}</Title>
              </div>
              <FaBoxes size={26} color="#228be6" />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Low Stock / Threshold Alerts
                </Text>
                <Title order={3} c={itemsBelowThreshold.length > 0 ? "red" : undefined}>
                  {itemsBelowThreshold.length}
                </Title>
              </div>
              <FaExclamationTriangle
                size={26}
                color={itemsBelowThreshold.length > 0 ? "#fa5252" : "#868e96"}
              />
            </Group>
          </Paper>

          <Paper withBorder p="md" radius="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Pending In-Charge Approvals
                </Text>
                <Title order={3}>{pendingRequests.length}</Title>
              </div>
              <FaPlus size={26} color="#fab005" />
            </Group>
          </Paper>
        </SimpleGrid>

        {/* Low Stock Warning Alert if any */}
        {itemsBelowThreshold.length > 0 && (
          <Alert
            icon={<FaExclamationCircle size={16} />}
            title="Immediate Replenishment Required"
            color="red"
          >
            {itemsBelowThreshold.length} item(s) are at or below their mandatory minimum safety threshold:{" "}
            <b>{itemsBelowThreshold.map((i) => `${i.name} (${i.current_quantity}/${i.minimum_threshold})`).join(", ")}</b>.
            Please submit replenishment requests to the VH In-Charge.
          </Alert>
        )}

        {/* Tabs: Inventory Stock & Replenishment Log */}
        <Card withBorder radius="md" p="md">
          <Tabs value={activeTab} onChange={setActiveTab}>
            <Tabs.List mb="md">
              <Tabs.Tab
                value="stock"
                leftSection={<FaBoxes size={14} />}
                rightSection={<Badge size="xs" circle color="blue">{(items || []).length}</Badge>}
              >
                Current Inventory Stock
              </Tabs.Tab>
              <Tabs.Tab
                value="replenishments"
                leftSection={<FaPlus size={14} />}
                rightSection={
                  <Badge size="xs" circle color={pendingRequests.length > 0 ? "orange" : "gray"}>
                    {(replenishments || []).length}
                  </Badge>
                }
              >
                Replenishment History
              </Tabs.Tab>
            </Tabs.List>

            {/* Current Stock Panel */}
            <Tabs.Panel value="stock">
              {loadingItems ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : (items || []).length === 0 ? (
                <Alert title="No Inventory Items Found" color="blue">
                  No inventory items have been configured yet.
                </Alert>
              ) : (
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Item Name</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Current Quantity</Table.Th>
                      <Table.Th>Min. Threshold</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Action</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {(items || []).map((item) => (
                      <Table.Tr key={item.id}>
                        <Table.Td>#{item.id}</Table.Td>
                        <Table.Td>
                          <Text fw={600} size="sm">{item.name}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge color={getCategoryColor(item.category)} variant="light">
                            {item.category}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text
                            fw={700}
                            size="sm"
                            c={item.is_below_threshold ? "red" : undefined}
                          >
                            {item.current_quantity}
                          </Text>
                        </Table.Td>
                        <Table.Td>{item.minimum_threshold}</Table.Td>
                        <Table.Td>
                          {item.is_below_threshold ? (
                            <Badge color="red" variant="filled">
                              BELOW THRESHOLD
                            </Badge>
                          ) : (
                            <Badge color="teal" variant="light">
                              Adequate
                            </Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Button
                            size="xs"
                            color={item.is_below_threshold ? "red" : "blue"}
                            variant={item.is_below_threshold ? "filled" : "light"}
                            leftSection={<FaPlus size={12} />}
                            onClick={() => handleOpenRequest(item)}
                          >
                            Request Restock
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>

            {/* Replenishments Panel */}
            <Tabs.Panel value="replenishments">
              {loadingReplenishments ? (
                <Group justify="center" p="xl">
                  <Loader size="md" />
                </Group>
              ) : (replenishments || []).length === 0 ? (
                <Alert title="No Replenishment Requests" color="blue">
                  No replenishment requests recorded yet.
                </Alert>
              ) : (
                <Table striped highlightOnHover withTableBorder withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Req ID</Table.Th>
                      <Table.Th>Item Name</Table.Th>
                      <Table.Th>Quantity Requested</Table.Th>
                      <Table.Th>Requested Date</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Remarks</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {(replenishments || []).map((rep) => (
                      <Table.Tr key={rep.id}>
                        <Table.Td>#{rep.id}</Table.Td>
                        <Table.Td>
                          <Text fw={600} size="sm">{rep.item_name}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge size="lg" color="blue" variant="light">
                            {rep.quantity_requested} units
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{new Date(rep.created_at).toLocaleDateString()}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            color={
                              rep.status === "APPROVED"
                                ? "teal"
                                : rep.status === "REJECTED"
                                ? "red"
                                : "yellow"
                            }
                          >
                            {rep.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{rep.remarks || "—"}</Text>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>
          </Tabs>
        </Card>
      </Stack>

      {/* Replenishment Request Modal */}
      <Modal
        opened={requestModalOpen}
        onClose={() => setRequestModalOpen(false)}
        title={<Text fw={600}>Request Inventory Replenishment</Text>}
      >
        <Stack gap="md">
          <Text size="sm">
            Submit a restocking requisition for <b>{selectedItem?.name}</b> to the VH In-Charge.
          </Text>
          <Group justify="space-between">
            <Text size="xs" c="dimmed">Current Stock: <b>{selectedItem?.current_quantity}</b></Text>
            <Text size="xs" c="dimmed">Threshold: <b>{selectedItem?.minimum_threshold}</b></Text>
          </Group>

          <NumberInput
            label="Replenishment Quantity"
            required
            min={1}
            max={500}
            value={requestQty}
            onChange={setRequestQty}
          />

          <Textarea
            label="Remarks / Justification"
            placeholder="E.g., Anticipating heavy occupancy next week..."
            value={requestRemarks}
            onChange={(e) => setRequestRemarks(e.target.value)}
          />

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRequestModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="blue"
              loading={requestReplenishment.isPending}
              onClick={handleConfirmRequest}
            >
              Submit Requisition
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
