import { useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Modal, NumberInput, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { useAddStock, useCreateInventoryItem, useInventoryItems } from "../api/hooks";
import type { InventoryItem } from "../api/types";

export default function InventoryPage() {
  const { can } = useAuth();
  const { data: items, isLoading } = useInventoryItems();
  const createItem = useCreateInventoryItem();

  const [createOpened, setCreateOpened] = useState(false);
  const [stockModalItem, setStockModalItem] = useState<InventoryItem | null>(null);

  const [itemCode, setItemCode] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("CONSUMABLE");
  const [initialQty, setInitialQty] = useState<number | string>(0);
  const [unit, setUnit] = useState("units");

  const [addQty, setAddQty] = useState<number | string>(1);
  const [addNotes, setAddNotes] = useState("");

  const addStockMutation = useAddStock(stockModalItem?.id ?? "");
  const canManage = can("dept.inventory.create");

  const handleCreate = async () => {
    if (!itemCode.trim() || !name.trim()) return;
    await createItem.mutateAsync({
      item_code: itemCode,
      name,
      category,
      initial_quantity: Number(initialQty),
      unit,
    });
    setItemCode("");
    setName("");
    setCreateOpened(false);
  };

  const handleAddStock = async () => {
    if (!stockModalItem || Number(addQty) <= 0) return;
    await addStockMutation.mutateAsync({
      quantity: Number(addQty),
      notes: addNotes,
    });
    setStockModalItem(null);
    setAddQty(1);
    setAddNotes("");
  };

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Department Inventory</Title>
          <Text c="dimmed">Track lab equipment, consumables, and stock balances</Text>
        </div>
        {canManage && (
          <Button onClick={() => setCreateOpened(true)}>New Inventory Item</Button>
        )}
      </Group>

      {isLoading && <Text>Loading inventory...</Text>}

      {items && items.length === 0 && (
        <Alert title="No Inventory Items" color="blue">
          No stock items have been recorded in this department.
        </Alert>
      )}

      {items && items.length > 0 && (
        <Card withBorder shadow="sm" radius="md">
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Code</Table.Th>
                <Table.Th>Item Name</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>In Stock</Table.Th>
                <Table.Th>Unit</Table.Th>
                {canManage && <Table.Th>Actions</Table.Th>}
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((i) => (
                <Table.Tr key={i.id}>
                  <Table.Td>{i.item_code}</Table.Td>
                  <Table.Td fw={500}>{i.name}</Table.Td>
                  <Table.Td>
                    <Badge color={i.category === "CONSUMABLE" ? "green" : "blue"}>{i.category}</Badge>
                  </Table.Td>
                  <Table.Td fw={700}>{i.quantity}</Table.Td>
                  <Table.Td>{i.unit}</Table.Td>
                  {canManage && (
                    <Table.Td>
                      <Button size="xs" variant="light" onClick={() => setStockModalItem(i)}>
                        Add Stock
                      </Button>
                    </Table.Td>
                  )}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <Modal opened={createOpened} onClose={() => setCreateOpened(false)} title="Add Inventory Item">
        <Stack gap="sm">
          <TextInput label="Item Code" placeholder="e.g. LAB-PC-01" value={itemCode} onChange={(e) => setItemCode(e.target.value)} required />
          <TextInput label="Name" placeholder="e.g. HDMI Cable" value={name} onChange={(e) => setName(e.target.value)} required />
          <Select
            label="Category"
            data={["EQUIPMENT", "CONSUMABLE", "FURNITURE", "OTHER"]}
            value={category}
            onChange={(val) => setCategory(val ?? "CONSUMABLE")}
          />
          <NumberInput label="Initial Quantity" value={initialQty} onChange={setInitialQty} min={0} />
          <TextInput label="Unit" placeholder="e.g. units, boxes" value={unit} onChange={(e) => setUnit(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate} loading={createItem.isPending}>Save</Button>
          </Group>
        </Stack>
      </Modal>

      <Modal opened={!!stockModalItem} onClose={() => setStockModalItem(null)} title={`Add Stock: ${stockModalItem?.name}`}>
        <Stack gap="sm">
          <NumberInput label="Quantity to Add" value={addQty} onChange={setAddQty} min={1} required />
          <TextInput label="Notes" placeholder="Reason or PO number" value={addNotes} onChange={(e) => setAddNotes(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setStockModalItem(null)}>Cancel</Button>
            <Button onClick={handleAddStock} loading={addStockMutation.isPending}>Add</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
