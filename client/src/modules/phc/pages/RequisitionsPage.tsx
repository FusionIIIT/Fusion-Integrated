import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Text, TextInput,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAllInventory, useRequisitionTransition, useRequisitions, useSubmitRequisition,
} from "../api/hooks";
import { ListStates } from "../components/ListStates";
import { LoadMore } from "../components/LoadMore";

const EVENT_LABELS: Record<string, string> = {
  approve: "Approve", reject: "Reject", fulfill: "Mark fulfilled",
};

function NewRequisitionModal({ onClose }: { onClose: () => void }) {
  const submit = useSubmitRequisition();
  const items = useAllInventory(true);
  const [purpose, setPurpose] = useState("");
  const [lines, setLines] = useState([{ item_id: "", quantity: "" }]);
  const setLine = (i: number, patch: Partial<(typeof lines)[number]>) =>
    setLines(lines.map((l, j) => (j === i ? { ...l, ...patch } : l)));

  return (
    <FormModal
      opened onClose={onClose} title="New procurement requisition" submitLabel="Submit"
      submitting={submit.isPending} error={submit.error}
      disabled={!purpose.trim() || lines.some((l) => !l.item_id || !l.quantity)}
      disabledReason="Enter the purpose and an item and quantity on every line."
      onSubmit={() => submit.mutate({
        purpose, lines: lines.map((l) => ({ item_id: Number(l.item_id), quantity: l.quantity })),
      }, { onSuccess: onClose })}
    >
      <Stack>
        <TextInput label="Purpose" required value={purpose}
          onChange={(e) => setPurpose(e.currentTarget.value)} />
        {lines.map((line, i) => (
          <Group key={i} grow align="flex-end">
            <Select label={`Item ${i + 1}`} required value={line.item_id || null}
              onChange={(v) => setLine(i, { item_id: v ?? "" })}
              data={(items.data ?? []).map((it) => ({
                value: String(it.id), label: `${it.name} (${it.unit})`,
              }))} />
            <TextInput label="Quantity" required inputMode="decimal" value={line.quantity}
              onChange={(e) => setLine(i, { quantity: e.currentTarget.value })} />
          </Group>
        ))}
        <Button variant="light" onClick={() => setLines([...lines, { item_id: "", quantity: "" }])}>
          Add item
        </Button>
      </Stack>
    </FormModal>
  );
}

export default function RequisitionsPage() {
  const { can } = useAuth();
  const list = useRequisitions();
  const { data, isPending, error } = list;
  const transition = useRequisitionTransition();
  const [creating, setCreating] = useState(false);
  const rows = data?.results ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="Procurement requisitions"
        subtitle="Requests for supplies and their decisions"
        action={can("phc.requisition.create") && (
          <Button onClick={() => setCreating(true)}>New requisition</Button>
        )}
      />
      {transition.error != null && <Text c="red" mb="sm">{errorMessage(transition.error)}</Text>}
      <ListStates isPending={isPending} error={error} empty={rows.length === 0}
        emptyText="No requisitions" />
      <Stack>
        {rows.map((r) => (
          <Card key={r.id} withBorder padding="lg">
            <Group justify="space-between">
              <Text fw={700}>Requisition #{r.id}: {r.purpose}</Text>
              <Badge variant="light">{r.status_label}</Badge>
            </Group>
            {r.lines.map((l) => (
              <Text key={l.item} size="sm">{l.item_name}: {l.quantity} {l.unit}</Text>
            ))}
            {r.decision_note && <Text size="sm" c="dimmed">Note: {r.decision_note}</Text>}
            {r.allowed_events.length > 0 && (
              <Group mt="sm" gap="xs">
                {r.allowed_events.map((event) => (
                  <Button key={event} size="xs" color={event === "reject" ? "red" : undefined}
                    loading={transition.isPending}
                    onClick={() => transition.mutate({ id: r.id, event, note: "" })}>
                    {EVENT_LABELS[event] ?? event}
                  </Button>
                ))}
              </Group>
            )}
          </Card>
        ))}
      </Stack>
      <LoadMore list={list} />
      {creating && <NewRequisitionModal onClose={() => setCreating(false)} />}
    </Container>
  );
}
