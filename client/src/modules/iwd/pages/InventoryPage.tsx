import { useEffect, useState } from "react";
import { Badge, Button, Group, Paper, Stack, Table, Text, Title } from "@mantine/core";

type InventoryItem = {
  id: number; name: string; unit: string;
  quantity_available: string; unit_cost: string;
  minimum_stock: string; is_low_stock: boolean;
};

export default function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/v1/iwd/inventory/")
      .then((r) => r.json())
      .then((data) => { setItems(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <Text>Loading inventory...</Text>;

  return (
    <Stack gap="md" p="md">
      <Group justify="space-between">
        <Title order={2}>Inventory</Title>
        <Button size="sm" variant="outline" onClick={() => fetch("/api/v1/iwd/inventory/low_stock/").then(r=>r.json()).then(setItems)}>
          Show Low Stock
        </Button>
      </Group>
      <Paper shadow="xs" withBorder>
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Item</Table.Th><Table.Th>Unit</Table.Th>
              <Table.Th>Available</Table.Th><Table.Th>Min Stock</Table.Th>
              <Table.Th>Unit Cost</Table.Th><Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {items.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>{item.name}</Table.Td>
                <Table.Td>{item.unit}</Table.Td>
                <Table.Td>{item.quantity_available}</Table.Td>
                <Table.Td>{item.minimum_stock}</Table.Td>
                <Table.Td>Rs. {item.unit_cost}</Table.Td>
                <Table.Td>
                  {item.is_low_stock
                    ? <Badge color="red">Low Stock</Badge>
                    : <Badge color="green">OK</Badge>}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
        {items.length === 0 && <Text ta="center" c="dimmed" p="md">No inventory items found.</Text>}
      </Paper>
    </Stack>
  );
}

