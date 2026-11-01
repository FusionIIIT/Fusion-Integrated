import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Table,
  Tabs, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAddInventory, useDecideStock, useInventory, useIssueStock,
  useRequestStock, useStockLog, useStockRequests,
} from "../api/hooks";
import type { StockStatus } from "../api/types";

const STATUS: Record<StockStatus, { label: string; color: string }> = {
  pending_hod: { label: "Awaiting HOD", color: "yellow" },
  approved: { label: "Approved — to issue", color: "blue" },
  rejected: { label: "Rejected", color: "red" },
  issued: { label: "Issued", color: "green" },
};

const fail = (title: string) => (e: unknown) =>
  notifications.show({ color: "red", title, message: errorMessage(e) });

export default function StockPage() {
  const { can } = useAuth();
  const inventory = useInventory();
  const requests = useStockRequests();
  const decide = useDecideStock();
  const issue = useIssueStock();
  const canLog = can("dept.stock_log.view");
  const log = useStockLog(canLog);

  const [requesting, setRequesting] = useState(false);
  const [adding, setAdding] = useState(false);

  const error = inventory.error ?? requests.error;
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  return (
    <Container size="lg">
      <PageHeader
        title="Stock & inventory"
        subtitle="Request items, approve requests and issue approved stock"
        action={(
          <Group>
            {can("dept.inventory.manage") && (
              <Button variant="default" leftSection={<FaPlus size={12} />}
                      onClick={() => setAdding(true)}>Add stock</Button>
            )}
            {can("dept.stock_request.create") && (
              <Button leftSection={<FaPlus size={12} />}
                      onClick={() => setRequesting(true)}>Request stock</Button>
            )}
          </Group>
        )}
      />

      <Tabs defaultValue="requests">
        <Tabs.List mb="md">
          <Tabs.Tab value="requests">Requests</Tabs.Tab>
          <Tabs.Tab value="inventory">Inventory</Tabs.Tab>
          {canLog && <Tabs.Tab value="log">Movement log</Tabs.Tab>}
        </Tabs.List>

        <Tabs.Panel value="requests">
          <Card withBorder padding={0}>
            <Table verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Item</Table.Th><Table.Th>Qty</Table.Th>
                  <Table.Th>Purpose</Table.Th><Table.Th>Status</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(requests.data ?? []).map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.item_name}</Table.Td>
                    <Table.Td>{r.quantity} {r.unit}</Table.Td>
                    <Table.Td>{r.purpose || "—"}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" color={STATUS[r.status].color}>
                        {STATUS[r.status].label}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4} justify="flex-end" wrap="nowrap">
                        {r.status === "pending_hod" && can("dept.stock_request.decide") && (
                          <>
                            <Button size="xs" color="green" loading={decide.isPending}
                              onClick={() => decide.mutate(
                                { id: r.id, approve: true, note: "" },
                                { onError: fail("Could not approve") })}>
                              Approve
                            </Button>
                            <Button size="xs" color="red" variant="light"
                              loading={decide.isPending}
                              onClick={() => decide.mutate(
                                { id: r.id, approve: false, note: "" },
                                { onError: fail("Could not reject") })}>
                              Reject
                            </Button>
                          </>
                        )}
                        {r.status === "approved" && can("dept.stock_request.issue") && (
                          <Button size="xs" loading={issue.isPending}
                            onClick={() => issue.mutate(r.id,
                              { onError: fail("Could not issue") })}>
                            Issue
                          </Button>
                        )}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            {!requests.isPending && (requests.data ?? []).length === 0 && (
              <Text c="dimmed" p="lg" ta="center">No stock requests yet</Text>
            )}
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="inventory">
          <Card withBorder padding={0}>
            <Table verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Item</Table.Th><Table.Th>Category</Table.Th>
                  <Table.Th>In stock</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(inventory.data ?? []).map((i) => (
                  <Table.Tr key={i.id}>
                    <Table.Td>{i.name}</Table.Td>
                    <Table.Td>{i.category || "—"}</Table.Td>
                    <Table.Td>
                      <Badge variant="light" color={i.quantity === 0 ? "red" : "gray"}>
                        {i.quantity} {i.unit}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        {canLog && (
          <Tabs.Panel value="log">
            <Card withBorder padding={0}>
              <Table verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>When</Table.Th><Table.Th>Item</Table.Th>
                    <Table.Th>Movement</Table.Th><Table.Th>Qty</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {(log.data ?? []).map((m) => (
                    <Table.Tr key={m.id}>
                      <Table.Td>{new Date(m.at).toLocaleString()}</Table.Td>
                      <Table.Td>{m.item_name}</Table.Td>
                      <Table.Td>{m.kind === "insert" ? "Inserted" : "Issued"}</Table.Td>
                      <Table.Td>{m.kind === "insert" ? "+" : "−"}{m.quantity}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>
        )}
      </Tabs>

      <RequestModal opened={requesting} onClose={() => setRequesting(false)}
                    items={inventory.data ?? []} />
      <AddModal opened={adding} onClose={() => setAdding(false)} />
    </Container>
  );
}

function RequestModal({ opened, onClose, items }: {
  opened: boolean; onClose: () => void;
  items: { id: number; name: string; quantity: number; unit: string }[];
}) {
  const request = useRequestStock();
  const [item, setItem] = useState<string | null>(null);
  const [qty, setQty] = useState<number | string>(1);
  const [purpose, setPurpose] = useState("");
  const chosen = items.find((i) => String(i.id) === item);

  return (
    <FormModal
      opened={opened} onClose={onClose} title="Request stock"
      subtitle="Checked against what is in stock right now"
      submitLabel="Send for approval" submitting={request.isPending}
      disabled={!chosen || Number(qty) < 1}
      error={request.error}
      onSubmit={() => chosen && request.mutate(
        { item: chosen.id, quantity: Number(qty), purpose },
        { onSuccess: () => { setItem(null); setQty(1); setPurpose(""); onClose(); } },
      )}
    >
      <Stack>
        <Select label="Item" required searchable value={item} onChange={setItem}
                data={items.map((i) => ({
                  value: String(i.id),
                  label: `${i.name} (${i.quantity} ${i.unit} in stock)`,
                  disabled: i.quantity === 0,
                }))} />
        <NumberInput label="Quantity" min={1} max={chosen?.quantity} value={qty}
                     onChange={setQty} allowDecimal={false} />
        <Textarea label="Purpose" autosize minRows={2} maxLength={300} value={purpose}
                  onChange={(e) => setPurpose(e.currentTarget.value)} />
      </Stack>
    </FormModal>
  );
}

function AddModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const add = useAddInventory();
  const [name, setName] = useState("");
  const [qty, setQty] = useState<number | string>(1);
  const [category, setCategory] = useState("");

  return (
    <FormModal
      opened={opened} onClose={onClose} title="Add stock"
      subtitle="An existing item name is topped up; every insertion is logged"
      submitLabel="Add" submitting={add.isPending}
      disabled={!name.trim() || Number(qty) < 1} error={add.error}
      onSubmit={() => add.mutate(
        { name, quantity: Number(qty), category },
        { onSuccess: () => { setName(""); setQty(1); setCategory(""); onClose(); } },
      )}
    >
      <Stack>
        <TextInput label="Item name" required value={name}
                   onChange={(e) => setName(e.currentTarget.value)} />
        <NumberInput label="Quantity" min={1} value={qty} onChange={setQty}
                     allowDecimal={false} />
        <TextInput label="Category" value={category}
                   onChange={(e) => setCategory(e.currentTarget.value)} />
      </Stack>
    </FormModal>
  );
}
