import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaClipboardList, FaPlus, FaTrash } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateRequisition, useFulfillRequisition, useInventoryItems,
} from "../api/hooks";
import type { Requisition, RequisitionItemInput } from "../api/types";

export default function RequisitionsPage() {
  const { data, error } = useInventoryItems();
  const { can } = useAuth();
  const create = useCreateRequisition();
  const fulfill = useFulfillRequisition();
  const canSubmit = can("phc.requisition.submit");
  const canFulfill = can("phc.requisition.fulfill");
  const [itemId, setItemId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState<string | number>(1);
  const [lines, setLines] = useState<RequisitionItemInput[]>([]);
  const [submitted, setSubmitted] = useState<Requisition[]>([]);
  const [fulfillId, setFulfillId] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const options = (data?.results ?? []).map((i) => ({
    value: String(i.id), label: `${i.name} · ${i.quantity} ${i.unit}`,
  }));

  function addLine() {
    if (!itemId || Number(quantity) < 1) return;
    setLines((prev) => [...prev, { item_id: Number(itemId), quantity: Number(quantity) }]);
    setItemId(null);
    setQuantity(1);
  }

  function submit() {
    create.mutate({ items: lines }, {
      onSuccess: (requisition) => {
        setSubmitted((prev) => [requisition, ...prev]);
        setLines([]);
        notifications.show({
          color: "green", title: "Requisition submitted",
          message: `Requisition #${requisition.requisition_id} awaits a decision.`,
        });
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not submit requisition", message: errorMessage(e),
      }),
    });
  }

  function doFulfill(id: number) {
    fulfill.mutate(id, {
      onSuccess: (requisition) => {
        setSubmitted((prev) => prev.map((r) =>
          r.requisition_id === requisition.requisition_id ? requisition : r));
        setFulfillId("");
        notifications.show({
          color: "green", title: "Requisition fulfilled",
          message: `Requisition #${id} is marked fulfilled.`,
        });
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not fulfill", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Procurement Requisitions"
        subtitle="Request stock and track the requisitions raised in this session"
      />

      {!canSubmit && (
        <Text c="red" size="sm" mb="md">
          You do not have permission to submit requisitions.
        </Text>
      )}

      {canSubmit && (
        <Card padding="lg" mb="md">
          <Stack gap="md">
            <Group align="flex-end" grow>
              <Select
                label="Item" searchable data={options} value={itemId}
                onChange={setItemId} placeholder={data ? "Select" : "Loading…"}
              />
              <NumberInput
                label="Quantity" min={1} value={quantity}
                onChange={setQuantity}
              />
              <Button variant="light" onClick={addLine}
                leftSection={<FaPlus size={11} />}
                disabled={!itemId || Number(quantity) < 1}
              >
                Add line
              </Button>
            </Group>

            {create.error && <ErrorState error={create.error} />}

            <DataTable<RequisitionItemInput & { name: string }>
              rows={lines.map((line) => ({
                ...line,
                name: data?.results.find((i) => i.id === line.item_id)?.name
                  ?? `Item ${line.item_id}`,
              }))}
              rowKey={(r) => `${r.item_id}-${r.quantity}`}
              minWidth={520}
              columns={[
                { key: "name", header: "Item",
                  render: (r) => <Text fw={600}>{r.name}</Text> },
                { key: "quantity", header: "Quantity", align: "right" },
                {
                  key: "remove", header: "", align: "right",
                  render: (r) => (
                    <Button
                      size="xs" variant="subtle" color="red"
                      aria-label="Remove line"
                      onClick={() => setLines((prev) => prev.filter(
                        (l) => !(l.item_id === r.item_id
                          && l.quantity === r.quantity)))}
                    >
                      <FaTrash size={11} />
                    </Button>
                  ),
                },
              ]}
              empty={{
                icon: FaClipboardList,
                title: "No line items",
                description: "Choose an item and quantity, then add it to the request.",
              }}
            />

            <Group justify="flex-end">
              <Button
                onClick={submit} loading={create.isPending}
                disabled={lines.length === 0}
              >
                Submit requisition
              </Button>
            </Group>
          </Stack>
        </Card>
      )}

      <Card padding="lg" mb="md">
        <Text fw={600} mb="sm">Submitted in this session</Text>
        {fulfill.error && <ErrorState error={fulfill.error} />}
        <DataTable<Requisition>
          rows={submitted}
          rowKey={(r) => r.requisition_id}
          minWidth={720}
          columns={[
            { key: "id", header: "Requisition",
              render: (r) => <Text fw={600}>#{r.requisition_id}</Text> },
            { key: "state", header: "State",
              render: (r) => <Badge variant="light" size="sm">{r.state.replace(/_/g, " ")}</Badge> },
            { key: "created_at", header: "Raised",
              render: (r) => new Date(r.created_at).toLocaleString() },
          ]}
          empty={{
            icon: FaClipboardList,
            title: "No requisitions submitted yet",
            description: "Requisitions you raise will be listed here.",
          }}
        />
      </Card>

      {canFulfill && (
        <Card padding="lg">
          <Text fw={600} mb="sm">Mark an approved requisition fulfilled</Text>
          <Group align="flex-end">
            <TextInput
              label="Requisition number" type="number" min={1}
              value={fulfillId} placeholder="e.g. 42"
              onChange={(e) => setFulfillId(e.currentTarget.value)} w={240}
            />
            <Button
              variant="light" loading={fulfill.isPending}
              onClick={() => doFulfill(Number(fulfillId))}
              disabled={!fulfillId || Number(fulfillId) < 1}
            >
              Mark fulfilled
            </Button>
          </Group>
        </Card>
      )}
    </Container>
  );
}
