import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAddStock, useInventory, useRequestStock, useStockAction, useStockRequests,
} from "../api/hooks";

export default function InventoryPage() {
  const { can, session } = useAuth();
  const inventory = useInventory();
  const requests = useStockRequests();
  const addStock = useAddStock();
  const requestStock = useRequestStock();
  const act = useStockAction();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState<number | string>(1);
  const [itemId, setItemId] = useState<string | null>(null);
  const [requestQuantity, setRequestQuantity] = useState<number | string>(1);
  const [note, setNote] = useState("");
  const activeRole = (session?.active_role ?? "").toLowerCase().replaceAll(" ", "_");
  const canAdd = can("department.inventory.manage");
  const canRequest = can("department.stock_request.create");
  const canDecide = activeRole === "hod" && can("department.stock_request.review");
  const canIssue = activeRole === "dept_admin" && can("department.stock_request.issue");

  if (inventory.error) return <Container size="md"><ErrorState error={inventory.error} /></Container>;
  if (requests.error) return <Container size="md"><ErrorState error={requests.error} /></Container>;

  function add() {
    addStock.mutate({ name: name.trim(), description, quantity: Number(quantity) }, {
      onSuccess: () => {
        setName(""); setDescription(""); setQuantity(1);
        notifications.show({ title: "Inventory updated", message: "The stock movement was recorded." });
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not add stock", message: errorMessage(e),
      }),
    });
  }

  function submitRequest() {
    if (!itemId) return;
    requestStock.mutate({ item_id: Number(itemId), quantity: Number(requestQuantity) }, {
      onSuccess: () => notifications.show({
        title: "Request submitted", message: "It is pending HOD approval.",
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not request stock", message: errorMessage(e),
      }),
    });
  }

  function runAction(id: number, action: string) {
    act.mutate({ id, action, note }, {
      onSuccess: () => setNote(""),
      onError: (e) => notifications.show({
        color: "red", title: "Could not update request", message: errorMessage(e),
      }),
    });
  }

  const items = inventory.data?.items ?? [];
  const stockRequests = requests.data ?? [];
  const itemOptions = items.map((item) => ({ value: String(item.id),
    label: `${item.name} (${item.quantity} available)` }));

  return (
    <Container size="md">
      <PageHeader title="Department inventory"
        subtitle="Stock requests move from Faculty submission to HOD decision and Dept_Admin issuance." />

      {canAdd && (
        <Card withBorder padding="lg" mb="lg">
          <Stack>
            <Text fw={700}>Record a stock insertion</Text>
            <Group grow align="flex-end">
              <TextInput label="Item name" value={name}
                onChange={(e) => setName(e.currentTarget.value)} />
              <TextInput label="Description" value={description}
                onChange={(e) => setDescription(e.currentTarget.value)} />
              <NumberInput label="Quantity" min={1} value={quantity}
                onChange={setQuantity} />
            </Group>
            <Button onClick={add} loading={addStock.isPending}
              disabled={!name.trim() || Number(quantity) < 1}>Add stock</Button>
          </Stack>
        </Card>
      )}

      {canRequest && (
        <Card withBorder padding="lg" mb="lg">
          <Stack>
            <Text fw={700}>Request an inventory item</Text>
            <Group grow align="flex-end">
              <Select label="Item" data={itemOptions} value={itemId}
                onChange={setItemId} searchable />
              <NumberInput label="Quantity" min={1} value={requestQuantity}
                onChange={setRequestQuantity} />
              <Button onClick={submitRequest} loading={requestStock.isPending}
                disabled={!itemId || Number(requestQuantity) < 1}>Submit request</Button>
            </Group>
          </Stack>
        </Card>
      )}

      <Stack gap="lg">
        <section>
          <Text fw={700} mb="sm">Current stock</Text>
          {inventory.isPending ? <Text c="dimmed">Loading inventory…</Text>
            : items.length === 0 ? <Text c="dimmed">No inventory recorded yet.</Text>
            : <Stack gap="xs">{items.map((item) => (
              <Card key={item.id} withBorder padding="sm">
                <Group justify="space-between">
                  <div><Text fw={600}>{item.name}</Text>
                    {item.description && <Text size="sm" c="dimmed">{item.description}</Text>}</div>
                  <Badge variant="light">{item.quantity} available</Badge>
                </Group>
              </Card>
            ))}</Stack>}
        </section>

        <section>
          <Text fw={700} mb="sm">Stock requests</Text>
          {requests.isPending ? <Text c="dimmed">Loading requests…</Text>
            : stockRequests.length === 0 ? <Text c="dimmed">No stock requests yet.</Text>
            : <Stack gap="xs">{stockRequests.map((row) => (
              <Card key={row.id} withBorder padding="md">
                <Stack gap="xs">
                  <Group justify="space-between">
                    <Text fw={600}>{row.item_name} · {row.quantity}</Text>
                    <Badge color={row.status === "rejected" ? "red"
                      : row.status === "issued" ? "green" : "blue"}>
                      {row.status.replaceAll("_", " ")}
                    </Badge>
                  </Group>
                  <Text size="sm" c="dimmed">Requested by account {row.faculty_user_id}</Text>
                  {row.decision_note && <Text size="sm">{row.decision_note}</Text>}
                  {canDecide && row.status === "pending_hod_approval" && (
                    <>
                      <TextInput label="Decision note (optional)" value={note}
                        onChange={(e) => setNote(e.currentTarget.value)} />
                      <Group>
                        <Button size="xs" onClick={() => runAction(row.id, "approve")}>Approve</Button>
                        <Button size="xs" color="red" variant="light"
                          onClick={() => runAction(row.id, "reject")}>Reject</Button>
                      </Group>
                    </>
                  )}
                  {canIssue && row.status === "approved_for_issuance" && (
                    <Button size="xs" w="fit-content"
                      onClick={() => runAction(row.id, "issue")}>Mark issued</Button>
                  )}
                </Stack>
              </Card>
            ))}</Stack>}
        </section>

        <section>
          <Text fw={700} mb="sm">Stock movement history</Text>
          <Stack gap="xs">{(inventory.data?.movements ?? []).map((movement) => (
            <Card key={movement.id} withBorder padding="sm">
              <Group justify="space-between">
                <Text>{movement.item_name} · {movement.movement} · {movement.quantity}</Text>
                <Text size="xs" c="dimmed">{new Date(movement.created_at).toLocaleString()}</Text>
              </Group>
            </Card>
          ))}</Stack>
        </section>
      </Stack>
    </Container>
  );
}
