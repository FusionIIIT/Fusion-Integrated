import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Drawer,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExclamationTriangle, FaHistory, FaMinus, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAdjustStock,
  useInventoryItems,
  useSaveInventoryItem,
  useStockAdjustments,
} from "../api/hooks";
import type { InventoryItem } from "../api/types";

export default function InventoryStockPage() {
  const { can } = useAuth();
  const isStaff = can("phc.inventory.adjust");

  const { data: items, isPending, error } = useInventoryItems();
  const { data: adjustments } = useStockAdjustments();

  const [adjustModalOpen, setAdjustModalOpen] = useState(false);
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);

  // Adjustment form
  const [adjustmentType, setAdjustmentType] = useState<"ADD" | "DEDUCT">("ADD");
  const [adjustQty, setAdjustQty] = useState<number | string>(10);
  const [adjustReason, setAdjustReason] = useState("");

  // New item form
  const [itemCode, setItemCode] = useState("");
  const [itemName, setItemName] = useState("");
  const [category, setCategory] = useState("Medicine");
  const [reorderThreshold, setReorderThreshold] = useState<number | string>(10);
  const [unit, setUnit] = useState("units");

  const adjustStockMutation = useAdjustStock();
  const saveItemMutation = useSaveInventoryItem();

  const handleAdjustStock = async () => {
    if (!selectedItem || !adjustQty || !adjustReason) {
      notifications.show({ title: "Incomplete Form", message: "Quantity and reason are required.", color: "orange" });
      return;
    }

    try {
      const updated = await adjustStockMutation.mutateAsync({
        item_id: selectedItem.id,
        adjustment_type: adjustmentType,
        quantity: Number(adjustQty),
        reason: adjustReason,
      });

      notifications.show({
        title: "Stock Updated",
        message: `${selectedItem.name} stock updated to ${updated.stock_level} ${updated.unit} (audited).`,
        color: "teal",
      });
      setAdjustModalOpen(false);
      setAdjustReason("");
    } catch (err: any) {
      const msg = err.response?.data?.error || "Failed to update stock.";
      notifications.show({ title: "Adjustment Failed", message: msg, color: "red" });
    }
  };

  const handleCreateItem = async () => {
    if (!itemCode || !itemName) {
      notifications.show({ title: "Incomplete Form", message: "Code and name are required.", color: "orange" });
      return;
    }

    try {
      await saveItemMutation.mutateAsync({
        item_code: itemCode,
        name: itemName,
        category,
        reorder_threshold: Number(reorderThreshold),
        unit,
      });
      notifications.show({ title: "Item Added", message: `${itemName} registered in pharmacy catalog.`, color: "teal" });
      setItemModalOpen(false);
      setItemCode("");
      setItemName("");
    } catch {
      notifications.show({ title: "Error", message: "Failed to create inventory item.", color: "red" });
    }
  };

  if (error) return <ErrorState error={error} />;

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Pharmacy & Medical Inventory"
        subtitle="Manage stock levels, reorder thresholds, and low-stock alerts (AFR-PHC-024, 025, 026; PHC-BR-07)"
        action={
          <Group>
            <Button leftSection={<FaHistory />} variant="default" onClick={() => setHistoryDrawerOpen(true)}>
              Adjustment History
            </Button>
            {isStaff && (
              <Button leftSection={<FaPlus />} color="blue" onClick={() => setItemModalOpen(true)}>
                Add Catalog Item
              </Button>
            )}
          </Group>
        }
      />

      {isPending ? (
        <Text c="dimmed">Loading inventory...</Text>
      ) : !items || items.length === 0 ? (
        <Card withBorder p="xl">
          <Text c="dimmed" ta="center">
            No inventory items registered in the pharmacy catalog.
          </Text>
        </Card>
      ) : (
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Code</Table.Th>
              <Table.Th>Item Name</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Stock Level</Table.Th>
              <Table.Th>Reorder Threshold</Table.Th>
              <Table.Th>Status / Alert</Table.Th>
              {isStaff && <Table.Th>Action</Table.Th>}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td fw={600}>{item.item_code}</Table.Td>
                <Table.Td>{item.name}</Table.Td>
                <Table.Td>{item.category}</Table.Td>
                <Table.Td fw={700}>
                  {item.stock_level} {item.unit}
                </Table.Td>
                <Table.Td c="dimmed">
                  {item.reorder_threshold} {item.unit}
                </Table.Td>
                <Table.Td>
                  {item.is_low_stock ? (
                    <Badge color="red" variant="filled" leftSection={<FaExclamationTriangle size={11} />}>
                      Low Stock Warning
                    </Badge>
                  ) : (
                    <Badge color="green" variant="light">
                      Adequate Stock
                    </Badge>
                  )}
                </Table.Td>
                {isStaff && (
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="xs"
                        leftSection={<FaPlus />}
                        color="teal"
                        variant="light"
                        onClick={() => {
                          setSelectedItem(item);
                          setAdjustmentType("ADD");
                          setAdjustModalOpen(true);
                        }}
                      >
                        Add
                      </Button>
                      <Button
                        size="xs"
                        leftSection={<FaMinus />}
                        color="orange"
                        variant="light"
                        onClick={() => {
                          setSelectedItem(item);
                          setAdjustmentType("DEDUCT");
                          setAdjustModalOpen(true);
                        }}
                      >
                        Deduct
                      </Button>
                    </Group>
                  </Table.Td>
                )}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* Adjust Stock Modal */}
      <Modal
        opened={adjustModalOpen}
        onClose={() => setAdjustModalOpen(false)}
        title={`${adjustmentType === "ADD" ? "Add to" : "Deduct from"} Stock: ${selectedItem?.name}`}
      >
        <Stack>
          <Text size="sm">
            Current Stock: <b>{selectedItem?.stock_level} {selectedItem?.unit}</b> | Reorder Threshold: <b>{selectedItem?.reorder_threshold}</b>
          </Text>
          <NumberInput
            label="Quantity"
            value={adjustQty}
            onChange={setAdjustQty}
            min={1}
            required
          />
          <TextInput
            label="Reason for Adjustment"
            placeholder={adjustmentType === "ADD" ? "e.g. Received new shipment from vendor" : "e.g. Dispensed to OPD patients"}
            value={adjustReason}
            onChange={(e) => setAdjustReason(e.currentTarget.value)}
            required
          />
          <Button
            fullWidth
            color={adjustmentType === "ADD" ? "teal" : "orange"}
            onClick={handleAdjustStock}
            loading={adjustStockMutation.isPending}
          >
            Confirm Stock {adjustmentType === "ADD" ? "Addition" : "Deduction"}
          </Button>
        </Stack>
      </Modal>

      {/* Add Item Modal */}
      <Modal opened={itemModalOpen} onClose={() => setItemModalOpen(false)} title="Register New Catalog Item">
        <Stack>
          <TextInput label="Item Code" placeholder="e.g. MED-PCM-500" value={itemCode} onChange={(e) => setItemCode(e.currentTarget.value)} required />
          <TextInput label="Item Name" placeholder="e.g. Paracetamol 500mg" value={itemName} onChange={(e) => setItemName(e.currentTarget.value)} required />
          <Select label="Category" data={["Medicine", "Consumable", "Equipment", "First-Aid"]} value={category} onChange={(v) => setCategory(v || "Medicine")} />
          <Group grow>
            <NumberInput label="Reorder Threshold" value={reorderThreshold} onChange={setReorderThreshold} min={1} required />
            <TextInput label="Unit" placeholder="tablets / bottles / vials" value={unit} onChange={(e) => setUnit(e.currentTarget.value)} required />
          </Group>
          <Button fullWidth color="blue" onClick={handleCreateItem} loading={saveItemMutation.isPending}>
            Save Item
          </Button>
        </Stack>
      </Modal>

      {/* Adjustment History Drawer */}
      <Drawer opened={historyDrawerOpen} onClose={() => setHistoryDrawerOpen(false)} title="Stock Adjustment Audit History" position="right" size="lg">
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Time</Table.Th>
              <Table.Th>Item</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Qty</Table.Th>
              <Table.Th>Stock Change</Table.Th>
              <Table.Th>Reason</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(adjustments || []).map((a) => (
              <Table.Tr key={a.id}>
                <Table.Td>{new Date(a.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td fw={500}>{a.item_name}</Table.Td>
                <Table.Td>
                  <Badge size="xs" color={a.adjustment_type === "ADD" ? "teal" : "orange"}>
                    {a.adjustment_type}
                  </Badge>
                </Table.Td>
                <Table.Td>{a.quantity}</Table.Td>
                <Table.Td>
                  {a.previous_stock} → {a.new_stock}
                </Table.Td>
                <Table.Td>{a.reason}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Drawer>
    </Container>
  );
}
