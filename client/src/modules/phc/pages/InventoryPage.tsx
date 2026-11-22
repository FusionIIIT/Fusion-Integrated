import { useState } from "react";
import { Alert, Badge, Button, Container, Group, Stack, Table, Text, TextInput } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAdjustStock, useCreateItem, useInventory, useLowStockAlerts } from "../api/hooks";
import type { InventoryItem } from "../api/types";
import { ListStates } from "../components/ListStates";

function AdjustModal({ item, onClose }: { item: InventoryItem; onClose: () => void }) {
  const adjust = useAdjustStock();
  const [delta, setDelta] = useState("");
  const [reason, setReason] = useState("");
  return (
    <FormModal
      opened onClose={onClose} title={`Adjust stock: ${item.name}`}
      subtitle={`In stock: ${item.stock_level} ${item.unit}`}
      submitting={adjust.isPending} error={adjust.error} disabled={!delta}
      disabledReason="Enter a positive number to add or a negative number to deduct."
      onSubmit={() => adjust.mutate({ id: item.id, delta, reason }, { onSuccess: onClose })}
    >
      <Stack>
        <TextInput label="Quantity to add (negative to deduct)" required inputMode="decimal"
          value={delta} onChange={(e) => setDelta(e.currentTarget.value)} />
        <TextInput label="Reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
      </Stack>
    </FormModal>
  );
}

function NewItemModal({ onClose }: { onClose: () => void }) {
  const create = useCreateItem();
  const [form, setForm] = useState({ name: "", unit: "", stock_level: "0",
    reorder_threshold: "0" });
  const field = (key: keyof typeof form, label: string) => (
    <TextInput label={label} required value={form[key]}
      onChange={(e) => setForm({ ...form, [key]: e.currentTarget.value })} />
  );
  return (
    <FormModal
      opened onClose={onClose} title="Add inventory item" submitting={create.isPending}
      error={create.error} disabled={!form.name.trim() || !form.unit.trim()}
      disabledReason="Enter the item's name and unit."
      onSubmit={() => create.mutate(form, { onSuccess: onClose })}
    >
      <Stack>
        {field("name", "Name")}
        {field("unit", "Unit")}
        {field("stock_level", "Opening stock")}
        {field("reorder_threshold", "Reorder threshold")}
      </Stack>
    </FormModal>
  );
}

export default function InventoryPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useInventory();
  const alerts = useLowStockAlerts();
  const [adjusting, setAdjusting] = useState<InventoryItem | null>(null);
  const [adding, setAdding] = useState(false);
  const rows = data?.results ?? [];
  const recentAlerts = alerts.data?.results.slice(0, 5) ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="Inventory"
        subtitle="Stock levels and low-stock alerts"
        action={can("phc.inventory.create") && (
          <Button onClick={() => setAdding(true)}>Add item</Button>
        )}
      />
      {recentAlerts.length > 0 && (
        <Alert color="orange" title="Low stock" mb="md">
          {recentAlerts.map((a) => (
            <Text key={a.id} size="sm">
              {a.item_name}: {a.level} left, threshold {a.threshold}
            </Text>
          ))}
        </Alert>
      )}
      <ListStates isPending={isPending} error={error} empty={rows.length === 0}
        emptyText="No inventory items yet" />
      {rows.length > 0 && (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Item</Table.Th><Table.Th>In stock</Table.Th>
              <Table.Th>Reorder at</Table.Th><Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>
                  <Group gap="xs">
                    {item.name}{item.is_low && <Badge color="orange" size="xs">Low</Badge>}
                  </Group>
                </Table.Td>
                <Table.Td>{item.stock_level} {item.unit}</Table.Td>
                <Table.Td>{item.reorder_threshold}</Table.Td>
                <Table.Td>
                  {can("phc.inventory.update") && (
                    <Button size="xs" variant="default" onClick={() => setAdjusting(item)}>
                      Adjust stock
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      {adjusting && <AdjustModal item={adjusting} onClose={() => setAdjusting(null)} />}
      {adding && <NewItemModal onClose={() => setAdding(false)} />}
    </Container>
  );
}
