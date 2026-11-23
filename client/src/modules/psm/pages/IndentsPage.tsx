// Purchase indents list, submission, modification, withdrawal, repeat, and approval actions.
import { useState } from "react";
import {
  Badge, Button, Card, Container, Drawer, Group, NumberInput, Select, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateIndent, useIndentAction, useIndentDetail, useIndents, useModifyIndent } from "../api/hooks";
import type { Indent } from "../api/types";

export default function IndentsPage() {
  const { can, session } = useAuth();
  const { data, isPending, error } = useIndents();
  const createIndent = useCreateIndent();
  const modifyIndent = useModifyIndent();
  const act = useIndentAction();
  const [creating, setCreating] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const detail = useIndentDetail(selectedId);

  const [department, setDepartment] = useState("CSE");
  const [itemId, setItemId] = useState<number | string>("");
  const [itemDesc, setItemDesc] = useState("");
  const [quantity, setQuantity] = useState<number | string>(1);
  const [estimatedCost, setEstimatedCost] = useState("1000.00");
  const [justification, setJustification] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function submitIndent() {
    createIndent.mutate(
      {
        department,
        ...(itemId !== "" && Number(itemId) > 0 ? { item_id: Number(itemId) } : {}),
        item_description: itemDesc,
        quantity: Number(quantity),
        estimated_cost: estimatedCost,
        justification,
        submit: true,
      },
      {
        onSuccess: () => {
          setCreating(false);
          setItemId("");
          setItemDesc("");
          setJustification("");
          notifications.show({ color: "green", title: "Indent submitted", message: "Your indent has entered review." });
        },
        onError: (e) => notifications.show({ color: "red", title: "Could not submit indent", message: errorMessage(e) }),
      },
    );
  }

  function runAction(id: number, action: string, body: Record<string, unknown> = {}) {
    act.mutate(
      { id, action, body },
      {
        onSuccess: () => notifications.show({ color: "green", title: "Updated", message: `Action '${action}' succeeded.` }),
        onError: (e) => notifications.show({ color: "red", title: "Action refused", message: errorMessage(e) }),
      },
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Purchase Indents"
        subtitle="Create, track, and process departmental purchase indents"
        action={
          can("psm.indent.create") ? (
            <Button onClick={() => setCreating(true)}>New indent</Button>
          ) : undefined
        }
      />

      <Card padding="lg">
        <DataTable<Indent>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No purchase indents found in your scope." }}
          columns={[
            {
              key: "indent_number",
              header: "Indent",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.indent_number ?? `Draft #${r.id}`}</Text>
                  <Text size="xs" c="dimmed">{r.department} · v{r.version}</Text>
                </Stack>
              ),
            },
            { key: "item", header: "Item", render: (r) => r.item_description },
            { key: "qty", header: "Qty / Cost", render: (r) => `${r.quantity} · ₹${r.estimated_cost}` },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Group gap={4}>
                  <Badge variant="light">{r.status}</Badge>
                  {r.is_duplicate_flagged && <Badge color="orange" variant="light">duplicate?</Badge>}
                </Group>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs" wrap="nowrap">
                  <Button size="xs" variant="subtle" onClick={() => setSelectedId(r.id)}>History</Button>
                  {can("psm.stock.update") && r.status === "submitted" && (
                    <Button size="xs" onClick={() => runAction(r.id, "stock-check")}>Check stock</Button>
                  )}
                  {can("psm.indent.review") && (r.status === "stock_reserved" || r.status === "external_required") && (
                    <Button size="xs" onClick={() => runAction(r.id, "review", { decision: "approve" })}>Approve review</Button>
                  )}
                  {can("psm.indent.approve") && r.status === "department_reviewed" && (
                    <Button size="xs" onClick={() => runAction(r.id, "recommend", { decision: "recommend" })}>Recommend</Button>
                  )}
                  {can("psm.procurement.review") && r.status === "hod_recommended" && (
                    <Button size="xs" onClick={() => runAction(r.id, "procurement-review")}>Select method</Button>
                  )}
                  {can("psm.procurement.approve") && r.status === "awaiting_final_approval" && (
                    <Button size="xs" onClick={() => runAction(r.id, "final-decision", { decision: "approve" })}>Final approve</Button>
                  )}
                  {can("psm.indent.create") && r.user_id === session?.user.id && (
                    <Button size="xs" variant="subtle" onClick={() => runAction(r.id, "repeat")}>Repeat</Button>
                  )}
                  {can("psm.indent.update") && r.user_id === session?.user.id && (r.status === "draft" || r.status === "submitted" || r.status === "changes_requested") && (
                    <Button
                      size="xs"
                      variant="subtle"
                      onClick={() =>
                        modifyIndent.mutate(
                          { id: r.id, body: { quantity: r.quantity + 1 } },
                          {
                            onSuccess: () => notifications.show({ color: "green", title: "Modified", message: "Indent quantity updated." }),
                            onError: (e) => notifications.show({ color: "red", title: "Modify refused", message: errorMessage(e) }),
                          },
                        )
                      }
                    >
                      Modify
                    </Button>
                  )}
                  {can("psm.indent.delete") && r.user_id === session?.user.id && r.status === "submitted" && (
                    <Button size="xs" variant="subtle" color="red" onClick={() => runAction(r.id, "withdraw", { reason: "Withdrawn" })}>
                      Withdraw
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Submit Purchase Indent"
        submitLabel="Submit indent"
        submitting={createIndent.isPending}
        onSubmit={submitIndent}
      >
        <Stack gap="sm">
          <Select
            label="Department"
            data={["CSE", "ECE", "ME", "Design", "NS", "Liberal Arts", "SM"]}
            value={department}
            onChange={(v) => setDepartment(v ?? "CSE")}
          />
          <TextInput label="Item description" value={itemDesc} onChange={(e) => setItemDesc(e.currentTarget.value)} required />
          <NumberInput label="Stock item ID (optional)" min={1} value={itemId} onChange={setItemId} />
          <NumberInput label="Quantity" min={1} value={quantity} onChange={setQuantity} required />
          <TextInput label="Estimated cost" value={estimatedCost} onChange={(e) => setEstimatedCost(e.currentTarget.value)} required />
          <Textarea label="Justification" value={justification} onChange={(e) => setJustification(e.currentTarget.value)} required />
        </Stack>
      </FormModal>

      <Drawer opened={selectedId != null} onClose={() => setSelectedId(null)} title="Indent History" position="right" size="md">
        {detail.data ? (
          <Stack gap="sm">
            <Text fw={600}>{detail.data.indent_number ?? `Draft #${detail.data.id}`}</Text>
            <Text size="sm">{detail.data.item_description} — Qty {detail.data.quantity}</Text>
            <Text size="xs" c="dimmed">Transitions ({detail.data.transitions.length})</Text>
            {detail.data.transitions.map((t, idx) => (
              <Card key={idx} padding="xs" withBorder>
                <Text size="xs" fw={600}>{t.from_status} → {t.to_status}</Text>
                <Text size="xs" c="dimmed">{t.actor_role}: {t.reason || "—"}</Text>
              </Card>
            ))}
          </Stack>
        ) : (
          <Text size="sm" c="dimmed">Loading history...</Text>
        )}
      </Drawer>
    </Container>
  );
}
