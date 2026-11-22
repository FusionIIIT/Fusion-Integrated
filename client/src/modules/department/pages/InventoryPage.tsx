import { Button, Group, NumberInput, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAddItem, useDecideStock, useInventoryItems, useIssueStock, useReceiveStock, useRequestStock,
  useStockMovements, useStockRequests,
} from "../api/hooks";
import type { InventoryItem } from "../api/types";
import { ActionError, PageBody, useDialog } from "../components/PageBody";
import { useCanAct } from "../components/acting";

type Dialog =
  | { kind: "add"; name: string; unit: string; quantity: number }
  | { kind: "receipt"; item: InventoryItem; quantity: number }
  | { kind: "request"; item: string | null; quantity: number; purpose: string };

export default function InventoryPage() {
  const can = useCanAct();
  const items = useInventoryItems();
  const requests = useStockRequests();
  const movements = useStockMovements(can("department.stock_movement.view"));
  const add = useAddItem();
  const receive = useReceiveStock();
  const request = useRequestStock();
  const decide = useDecideStock();
  const issue = useIssueStock();
  const { dialog: dialog, setDialog: setDialog, opened } = useDialog<Dialog>();
  const rows = items.data?.results ?? [];
  const reqs = requests.data?.results ?? [];
  const pending = dialog?.kind === "add" ? add : dialog?.kind === "receipt" ? receive : request;

  function submit() {
    if (!dialog) return;
    const done = { onSuccess: () => setDialog(null) };
    if (dialog.kind === "add") add.mutate({ name: dialog.name, unit: dialog.unit, quantity: dialog.quantity }, done);
    if (dialog.kind === "receipt") receive.mutate({ id: dialog.item.id, quantity: dialog.quantity }, done);
    if (dialog.kind === "request" && dialog.item) {
      request.mutate({ item: Number(dialog.item), quantity: dialog.quantity, purpose: dialog.purpose }, done);
    }
  }

  return (
    <PageBody
      isPending={items.isPending} error={items.error} isEmpty={rows.length === 0 && reqs.length === 0}
      emptyTitle="No inventory items yet"
      header={(
        <PageHeader
          title="Inventory & Stock" subtitle="Items, stock requests and the movement log"
          action={(
            <Group>
              {can("department.inventory_item.create") && (
                <Button onClick={() => setDialog({ kind: "add", name: "", unit: "unit", quantity: 1 })}>Add item</Button>
              )}
              {can("department.stock_request.create") && rows.length > 0 && (
                <Button variant="light" onClick={() => setDialog({ kind: "request", item: rows[0] ? String(rows[0].id) : null, quantity: 1, purpose: "" })}>
                  Request stock
                </Button>
              )}
            </Group>
          )}
        />
      )}
      overlays={(
        <FormModal
          opened={opened} onClose={() => setDialog(null)} onSubmit={submit}
          title={dialog?.kind === "add" ? "Add item" : dialog?.kind === "receipt" ? "Record receipt" : "Request stock"}
          submitLabel={dialog?.kind === "request" ? "Submit request" : "Save"}
          submitting={pending.isPending} error={pending.error}
          disabled={dialog?.kind === "request" && !dialog.item} disabledReason="Choose the item you need."
        >
          {dialog?.kind === "add" && (
            <Stack>
              <TextInput label="Item name" value={dialog.name} onChange={(e) => setDialog({ ...dialog, name: e.currentTarget.value })} />
              <TextInput label="Unit" value={dialog.unit} onChange={(e) => setDialog({ ...dialog, unit: e.currentTarget.value })} />
              <NumberInput label="Quantity received" min={1} value={dialog.quantity}
                onChange={(v) => setDialog({ ...dialog, quantity: Number(v) || 0 })} />
            </Stack>
          )}
          {dialog?.kind === "receipt" && (
            <NumberInput label={`Quantity of ${dialog.item.name} received`} min={1} value={dialog.quantity}
              onChange={(v) => setDialog({ ...dialog, quantity: Number(v) || 0 })} />
          )}
          {dialog?.kind === "request" && (
            <Stack>
              <Select label="Item" value={dialog.item} allowDeselect={false}
                data={rows.map((i) => ({ value: String(i.id), label: `${i.name} (${i.current_quantity} ${i.unit})` }))}
                onChange={(v) => setDialog({ ...dialog, item: v })} />
              <NumberInput label="Quantity" min={1} value={dialog.quantity}
                onChange={(v) => setDialog({ ...dialog, quantity: Number(v) || 0 })} />
              <TextInput label="Purpose" value={dialog.purpose}
                onChange={(e) => setDialog({ ...dialog, purpose: e.currentTarget.value })} />
            </Stack>
          )}
        </FormModal>
      )}
    >
      <ActionError errors={[decide.error, issue.error, requests.error]} />
      <Table striped withTableBorder>
        <Table.Thead>
          <Table.Tr><Table.Th>Item</Table.Th><Table.Th>In stock</Table.Th><Table.Th /></Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((i) => (
            <Table.Tr key={i.id}>
              <Table.Td>{i.name}</Table.Td>
              <Table.Td>{i.current_quantity} {i.unit}</Table.Td>
              <Table.Td>
                {can("department.inventory_item.create") && (
                  <Button size="xs" variant="light" onClick={() => setDialog({ kind: "receipt", item: i, quantity: 1 })}>
                    Record receipt
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

      <Title order={4} mt="xl" mb="sm">Stock requests</Title>
      {reqs.length === 0 ? <Text c="dimmed">No stock requests.</Text> : (
        <Table striped withTableBorder>
          <Table.Thead>
            <Table.Tr><Table.Th>#</Table.Th><Table.Th>Item</Table.Th><Table.Th>Quantity</Table.Th>
              <Table.Th>Status</Table.Th><Table.Th /></Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {reqs.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>{r.id}</Table.Td>
                <Table.Td>{r.item_name}</Table.Td>
                <Table.Td>{r.quantity} {r.unit}</Table.Td>
                <Table.Td><StatusBadge status={r.status} /></Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {r.status === "pending_hod" && can("department.stock_request.approve") && (
                      <>
                        <Button size="xs" onClick={() => decide.mutate({ id: r.id, approve: true })}>Approve</Button>
                        <Button size="xs" color="red" variant="light"
                          onClick={() => decide.mutate({ id: r.id, approve: false })}>Reject</Button>
                      </>
                    )}
                    {r.status === "approved" && can("department.stock_issue.create") && (
                      <Button size="xs" onClick={() => issue.mutate(r.id)}>Issue</Button>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {can("department.stock_movement.view") && (
        <>
          <Title order={4} mt="xl" mb="sm">Movement log</Title>
          {(movements.data?.results ?? []).length === 0 ? <Text c="dimmed">No movements yet.</Text> : (
            <Table withTableBorder>
              <Table.Thead>
                <Table.Tr><Table.Th>When</Table.Th><Table.Th>Item</Table.Th><Table.Th>Kind</Table.Th>
                  <Table.Th>Quantity</Table.Th></Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(movements.data?.results ?? []).map((m) => (
                  <Table.Tr key={m.id}>
                    <Table.Td>{new Date(m.created_at).toLocaleString()}</Table.Td>
                    <Table.Td>{m.item_name}</Table.Td>
                    <Table.Td>{m.kind}</Table.Td>
                    <Table.Td>{m.quantity}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </>
      )}
    </PageBody>
  );
}
