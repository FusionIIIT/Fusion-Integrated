import { useEffect, useState } from "react";
import { Alert, Button, Container, NumberInput, Table, Text } from "@mantine/core";
import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { changeInventory, listInventory, type InventoryItem } from "../api";

export default function InventoryPage() {
  const [rows, setRows] = useState<InventoryItem[]>([]);
  const [delta, setDelta] = useState<Record<number, number>>({});
  const [error, setError] = useState("");
  async function refresh() {
    try { setRows(await listInventory()); setError(""); }
    catch (e) { setError(errorMessage(e)); }
  }
  useEffect(() => { void refresh(); }, []);
  async function update(item: InventoryItem) {
    try { await changeInventory(item.id, delta[item.id] ?? 0, "Inventory adjustment"); await refresh(); }
    catch (e) { setError(errorMessage(e)); }
  }
  return <Container size="xl"><PageHeader title="VH Inventory"
    subtitle="Current quantities and minimum thresholds." />
    {error && <Alert color="red" mb="md">{error}</Alert>}
    {!rows.length ? <Text c="dimmed">No inventory items found.</Text> :
      <Table><Table.Thead><Table.Tr><Table.Th>Item</Table.Th><Table.Th>Quantity</Table.Th>
        <Table.Th>Minimum</Table.Th><Table.Th>Adjustment</Table.Th><Table.Th /></Table.Tr></Table.Thead>
        <Table.Tbody>{rows.map((r) => <Table.Tr key={r.id}>
          <Table.Td>{r.name}</Table.Td><Table.Td>{r.current_quantity} {r.unit}</Table.Td>
          <Table.Td>{r.minimum_threshold} {r.unit}</Table.Td>
          <Table.Td><NumberInput value={delta[r.id] ?? 0} onChange={(v) => setDelta({ ...delta, [r.id]: Number(v) })} /></Table.Td>
          <Table.Td><Button size="xs" onClick={() => void update(r)}>Record</Button></Table.Td>
        </Table.Tr>)}</Table.Tbody></Table>}
  </Container>;
}
