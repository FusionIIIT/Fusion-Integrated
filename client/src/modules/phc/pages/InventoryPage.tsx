import { useState } from "react";
import { Button, Container, NumberInput, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage, http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useInventoryTransactions, useMedicines, usePhcPost } from "../api";
import { useAuth } from "../../../auth/AuthProvider";

export default function InventoryPage() {
  const { data, isPending, error, refetch } = useMedicines();
  const transactions = useInventoryTransactions();
  const { can } = useAuth();
  const [name, setName] = useState(""); const [unit, setUnit] = useState("");
  const [quantity, setQuantity] = useState<number | "">(1);
  const [threshold, setThreshold] = useState<number | "">(0); const [expiresOn, setExpiresOn] = useState("");
  const addMedicine = usePhcPost("/phc/medicines");
  if (error) return <Container><ErrorState error={error} /></Container>;
  const add = async () => { try { await addMedicine.mutateAsync({ name, unit,
    low_stock_threshold: threshold, expires_on: expiresOn || null }); setName(""); setUnit("");
    notifications.show({ message: "Medicine added to inventory", color: "green" }); }
    catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } };
  return <Container size="lg"><PageHeader title="Medicine Inventory" subtitle="Stock levels and expiry dates" />
    {can("phc.inventory.manage") && <Stack maw={480} mb="lg"><TextInput label="Medicine name" value={name} onChange={(e) => setName(e.currentTarget.value)} />
      <TextInput label="Unit" placeholder="tablet, bottle…" value={unit} onChange={(e) => setUnit(e.currentTarget.value)} />
      <NumberInput label="Low-stock threshold" min={0} value={threshold} onChange={(v) => setThreshold(typeof v === "number" ? v : "")} />
      <TextInput label="Expiry date" type="date" value={expiresOn} onChange={(e) => setExpiresOn(e.currentTarget.value)} />
      <Button onClick={add} disabled={!name || !unit} loading={addMedicine.isPending}>Add medicine</Button></Stack>}
    {isPending ? <Text c="dimmed">Loading inventory…</Text> : (data?.results ?? []).length === 0 ?
      <Text c="dimmed">No medicines in inventory.</Text> : <Table.ScrollContainer minWidth={650}><Table striped>
        <Table.Thead><Table.Tr><Table.Th>Medicine</Table.Th><Table.Th>Available</Table.Th><Table.Th>Expiry</Table.Th><Table.Th>Stock action</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{data?.results.map((m) => <Table.Tr key={m.id}><Table.Td>{m.name} ({m.unit})</Table.Td>
          <Table.Td>{m.quantity} {m.quantity <= m.low_stock_threshold && <Text span c="red"> · Low stock</Text>}</Table.Td>
          <Table.Td>{m.expires_on ?? "Not recorded"}</Table.Td><Table.Td>{can("phc.inventory.manage") && <Stack gap={4}>
            <NumberInput min={1} size="xs" value={quantity} onChange={(v) => setQuantity(typeof v === "number" ? v : "")} />
            <Button size="xs" variant="light" onClick={async () => { try {
              await http.post(`/phc/medicines/${m.id}/stock`, { action: "addition", quantity });
              await refetch(); await transactions.refetch(); notifications.show({ message: "Stock updated" });
            } catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } }}>Add stock</Button>
            <Button size="xs" color="red" variant="light" onClick={async () => { try {
              await http.post(`/phc/medicines/${m.id}/stock`, { action: "dispense", quantity });
              await refetch(); await transactions.refetch();
            } catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); } }}>Dispense</Button>
          </Stack>}</Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>}
    {can("phc.inventory.manage") && <>
      <Text fw={600} mt="xl" mb="sm">Recent stock transactions</Text>
      {transactions.isPending ? <Text c="dimmed">Loading stock history…</Text> :
        (transactions.data?.results ?? []).length === 0 ? <Text c="dimmed">No stock transactions yet.</Text> :
          <Table.ScrollContainer minWidth={700}><Table striped><Table.Thead><Table.Tr>
            <Table.Th>Date</Table.Th><Table.Th>Medicine</Table.Th><Table.Th>Action</Table.Th><Table.Th>Quantity</Table.Th><Table.Th>Actor ID</Table.Th><Table.Th>Patient ID</Table.Th>
          </Table.Tr></Table.Thead><Table.Tbody>{transactions.data?.results.map((t) => <Table.Tr key={t.id}>
            <Table.Td>{new Date(t.created_at).toLocaleString()}</Table.Td><Table.Td>{t.medicine_name}</Table.Td>
            <Table.Td>{t.transaction_type}</Table.Td><Table.Td>{t.quantity}</Table.Td><Table.Td>{t.actor_user_id}</Table.Td><Table.Td>{t.patient_id ?? "—"}</Table.Td>
          </Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>}
    </>}
  </Container>;
}
