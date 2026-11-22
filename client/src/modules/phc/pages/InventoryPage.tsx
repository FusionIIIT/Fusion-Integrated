import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBoxes, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAdjustStock, useCreateInventoryItem, useInventoryItems,
} from "../api/hooks";
import type { InventoryItem } from "../api/types";

const DIRECTIONS = [
  { value: "add", label: "Add to stock" },
  { value: "deduct", label: "Deduct from stock" },
];

export default function InventoryPage() {
  const { data, isPending, error } = useInventoryItems();
  const { can } = useAuth();
  const [creating, setCreating] = useState(false);
  const [adjusting, setAdjusting] = useState<InventoryItem | null>(null);
  const canAdjust = can("phc.inventory.adjust");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Inventory Stock"
        subtitle="Current stock levels and the adjustments recorded against them"
        action={canAdjust && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
            Add item
          </Button>
        )}
      />

      <Card padding="lg">
        <DataTable<InventoryItem>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={860}
          columns={[
            { key: "name", header: "Item",
              render: (r) => <Text fw={600}>{r.name}</Text> },
            { key: "unit", header: "Unit", render: (r) => r.unit || "—" },
            {
              key: "quantity", header: "In stock", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  <Text fw={600}>{r.quantity}</Text>
                  {r.quantity < r.reorder_threshold && (
                    <Badge color="orange" variant="light" size="sm">low</Badge>
                  )}
                </Group>
              ),
            },
            { key: "threshold", header: "Reorder at", align: "right",
              render: (r) => r.reorder_threshold },
            { key: "updated_at", header: "Updated",
              render: (r) => new Date(r.updated_at).toLocaleDateString() },
            {
              key: "actions", header: "", align: "right",
              render: (r) => canAdjust && (
                <Button
                  size="xs" variant="light" onClick={() => setAdjusting(r)}
                >
                  Adjust
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaBoxes,
            title: "No inventory items",
            description: canAdjust
              ? "Add an item to begin tracking stock."
              : "Stock items will appear here once added.",
          }}
        />
      </Card>

      {canAdjust && (
        <>
          <CreateModal opened={creating} onClose={() => setCreating(false)} />
          <AdjustModal item={adjusting} onClose={() => setAdjusting(null)} />
        </>
      )}
    </Container>
  );
}

function CreateModal({ opened, onClose }: {
  opened: boolean;
  onClose: () => void;
}) {
  const create = useCreateInventoryItem();
  const [name, setName] = useState("");
  const [unit, setUnit] = useState("units");
  const [threshold, setThreshold] = useState<string | number>(0);

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Add an inventory item"
      subtitle="Starts with zero stock; add a quantity separately"
      onSubmit={() => create.mutate(
        {
          name: name.trim(), unit: unit.trim() || "units",
          reorder_threshold: Number(threshold),
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green", title: "Item added",
              message: "Adjust the stock level when the item arrives.",
            });
            setName(""); setUnit("units"); setThreshold(0);
            onClose();
          },
          onError: (e) => notifications.show({
            color: "red", title: "Could not add item", message: errorMessage(e),
          }),
        },
      )}
      submitLabel="Add item" submitting={create.isPending}
      error={create.error} disabled={!name.trim()}
    >
      <Stack gap="md">
        <TextInput
          label="Item name" required value={name}
          onChange={(e) => setName(e.currentTarget.value)} maxLength={120}
        />
        <Group grow>
          <TextInput
            label="Unit" value={unit}
            onChange={(e) => setUnit(e.currentTarget.value)} maxLength={40}
          />
          <NumberInput
            label="Reorder threshold" value={threshold}
            onChange={setThreshold} min={0}
          />
        </Group>
      </Stack>
    </FormModal>
  );
}

function AdjustModal({ item, onClose }: {
  item: InventoryItem | null;
  onClose: () => void;
}) {
  const adjust = useAdjustStock();
  const [direction, setDirection] = useState<string | null>("add");
  const [quantity, setQuantity] = useState<string | number>(1);
  const [reason, setReason] = useState("");

  return (
    <FormModal
      opened={item != null} onClose={onClose}
      title={`Adjust ${item?.name ?? ""}`}
      subtitle={`Current stock: ${item?.quantity ?? 0} ${item?.unit ?? ""}`}
      onSubmit={() => item && adjust.mutate(
        {
          item_id: item.id, direction: direction as "add" | "deduct",
          quantity: Number(quantity), reason,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green", title: "Stock adjusted",
              message: `${item.name} has been updated.`,
            });
            setQuantity(1); setReason("");
            onClose();
          },
          onError: (e) => notifications.show({
            color: "red", title: "Could not adjust stock", message: errorMessage(e),
          }),
        },
      )}
      submitLabel="Record adjustment" submitting={adjust.isPending}
      error={adjust.error}
      disabled={!direction || Number(quantity) < 1}
    >
      <Stack gap="md">
        <Select
          label="Direction" required data={DIRECTIONS} value={direction}
          onChange={setDirection} allowDeselect={false}
        />
        <NumberInput
          label="Quantity" required min={1} value={quantity}
          onChange={setQuantity}
        />
        <TextInput
          label="Reason" value={reason}
          onChange={(e) => setReason(e.currentTarget.value)} maxLength={200}
          placeholder="Delivery, breakage, transfer…"
        />
      </Stack>
    </FormModal>
  );
}
