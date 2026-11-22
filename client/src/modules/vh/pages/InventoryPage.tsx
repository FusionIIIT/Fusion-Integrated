import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBoxes, FaExclamationTriangle, FaPlus, FaRedo } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useInventory,
  useRequestReplenishment,
  useSaveInventoryItem,
} from "../api/hooks";
import type { InventoryItem } from "../api/types";

export default function InventoryPage() {
  const { data: items, isPending, error } = useInventory();
  const [editingItem, setEditingItem] = useState<Partial<InventoryItem> | null>(null);
  const [replenishItem, setReplenishItem] = useState<InventoryItem | null>(null);
  const [replenishQty, setReplenishQty] = useState<number>(10);
  const [replenishRemarks, setReplenishRemarks] = useState("");

  const saveMutation = useSaveInventoryItem();
  const replenishMutation = useRequestReplenishment(replenishItem?.id ?? 0);

  const handleSaveItem = async () => {
    if (!editingItem?.item_name?.trim()) return;
    try {
      await saveMutation.mutateAsync(editingItem);
      notifications.show({ color: "teal", message: "Inventory item saved successfully." });
      setEditingItem(null);
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleReplenishSubmit = async () => {
    if (!replenishItem) return;
    try {
      await replenishMutation.mutateAsync({
        requested_quantity: replenishQty,
        remarks: replenishRemarks.trim(),
      });
      notifications.show({
        color: "teal",
        message: `Replenishment request submitted for ${replenishItem.item_name}.`,
      });
      setReplenishItem(null);
      setReplenishRemarks("");
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Inventory & Supplies"
        subtitle="Track stock levels, monitor automated threshold alerts, and requisition linen/consumables replenishment."
        action={
          <Button
            leftSection={<FaPlus size={12} />}
            onClick={() =>
              setEditingItem({
                item_name: "",
                category: "linen",
                current_quantity: 10,
                minimum_threshold: 5,
                unit: "pieces",
              })
            }
          >
            Add New Item
          </Button>
        }
      />

      <Card padding="lg" withBorder>
        <DataTable<InventoryItem>
          rows={items ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{
            icon: FaBoxes,
            title: "No inventory items registered",
            description: "Add new linen, consumables, or housekeeping supplies to begin tracking.",
          }}
          columns={[
            {
              key: "name",
              header: "Item Name",
              render: (r: InventoryItem) => (
                <Group gap="xs">
                  <Text fw={600} size="sm">
                    {r.item_name}
                  </Text>
                  {r.is_threshold_alert && (
                    <Tooltip label="Stock below minimum threshold!">
                      <Badge color="red" leftSection={<FaExclamationTriangle size={10} />}>
                        Low Stock
                      </Badge>
                    </Tooltip>
                  )}
                </Group>
              ),
            },
            {
              key: "category",
              header: "Category",
              render: (r: InventoryItem) => (
                <Badge variant="outline" color="blue">
                  {r.category}
                </Badge>
              ),
            },
            {
              key: "stock",
              header: "Current Stock",
              render: (r: InventoryItem) => `${r.current_quantity} ${r.unit}`,
            },
            {
              key: "threshold",
              header: "Minimum Threshold",
              render: (r: InventoryItem) => `${r.minimum_threshold} ${r.unit}`,
            },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r: InventoryItem) => (
                <Group gap="xs" justify="flex-end">
                  <Button
                    size="xs"
                    color="teal"
                    variant="light"
                    leftSection={<FaRedo size={10} />}
                    onClick={() => {
                      setReplenishItem(r);
                      setReplenishQty(Math.max(10, r.minimum_threshold * 2));
                      setReplenishRemarks("");
                    }}
                  >
                    Replenish
                  </Button>
                  <Button
                    size="xs"
                    variant="subtle"
                    onClick={() => setEditingItem(r)}
                  >
                    Edit
                  </Button>
                </Group>
              ),
            },
          ]}
        />
      </Card>

      {/* Edit / Add Modal */}
      <Modal
        opened={Boolean(editingItem)}
        onClose={() => setEditingItem(null)}
        title={editingItem?.id ? "Edit Inventory Item" : "Add Inventory Item"}
      >
        <Stack gap="md">
          <TextInput
            label="Item Name"
            required
            value={editingItem?.item_name ?? ""}
            onChange={(e) =>
              setEditingItem((prev) => ({ ...prev, item_name: e.currentTarget.value }))
            }
          />
          <Select
            label="Category"
            required
            data={[
              { value: "linen", label: "Linen & Bedding" },
              { value: "toiletries", label: "Toiletries & Hygiene" },
              { value: "crockery", label: "Crockery & Dining" },
              { value: "utensils", label: "Kitchen Utensils" },
              { value: "cleaning", label: "Housekeeping & Cleaning" },
              { value: "miscellaneous", label: "Miscellaneous" },
            ]}
            value={editingItem?.category ?? "linen"}
            onChange={(val) =>
              setEditingItem((prev) => ({
                ...prev,
                category: (val as InventoryItem["category"]) || "linen",
              }))
            }
          />
          <Group grow>
            <NumberInput
              label="Current Quantity"
              min={0}
              value={editingItem?.current_quantity ?? 0}
              onChange={(val) =>
                setEditingItem((prev) => ({ ...prev, current_quantity: Number(val) || 0 }))
              }
            />
            <NumberInput
              label="Minimum Threshold"
              min={1}
              value={editingItem?.minimum_threshold ?? 5}
              onChange={(val) =>
                setEditingItem((prev) => ({ ...prev, minimum_threshold: Number(val) || 1 }))
              }
            />
          </Group>
          <TextInput
            label="Unit"
            value={editingItem?.unit ?? "pieces"}
            onChange={(e) => setEditingItem((prev) => ({ ...prev, unit: e.currentTarget.value }))}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setEditingItem(null)}>
              Cancel
            </Button>
            <Button color="blue" onClick={handleSaveItem}>
              Save Item
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Replenish Request Modal */}
      <Modal
        opened={Boolean(replenishItem)}
        onClose={() => setReplenishItem(null)}
        title="Requisition Inventory Replenishment"
      >
        <Stack gap="md">
          <Text size="sm">
            Submitting replenishment requirement for <strong>{replenishItem?.item_name}</strong> to VH In-Charge for approval.
          </Text>
          <NumberInput
            label="Requested Quantity"
            min={1}
            required
            value={replenishQty}
            onChange={(val) => setReplenishQty(Number(val) || 1)}
          />
          <TextInput
            label="Purpose / Remarks"
            placeholder="Stock restock for upcoming institute convocation"
            value={replenishRemarks}
            onChange={(e) => setReplenishRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setReplenishItem(null)}>
              Cancel
            </Button>
            <Button color="teal" onClick={handleReplenishSubmit}>
              Submit to In-Charge
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
