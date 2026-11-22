import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Select, Stack, Text, TextInput, Timeline,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useClaimTransition, useClaims, useEligiblePrescriptions, useSubmitClaim,
} from "../api/hooks";
import { ListStates } from "../components/ListStates";

const EVENT_LABELS: Record<string, string> = {
  forward: "Forward to Accounts", verify: "Mark verified", approve: "Approve sanction",
  reject: "Reject", pay: "Record payment",
};

function SubmitClaimModal({ onClose }: { onClose: () => void }) {
  const submit = useSubmitClaim();
  const prescriptions = useEligiblePrescriptions(true);
  const [prescription, setPrescription] = useState<string | null>(null);
  const [expenseDate, setExpenseDate] = useState("");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");

  return (
    <FormModal
      opened onClose={onClose} title="New reimbursement claim"
      subtitle="A submitted claim cannot be changed; a correction is a new claim."
      submitLabel="Submit claim" submitting={submit.isPending} error={submit.error}
      disabled={!prescription || !expenseDate || !amount}
      disabledReason="Choose the prescription and enter the expense date and amount."
      onSubmit={() => submit.mutate({
        prescription_id: Number(prescription), expense_date: expenseDate, amount, description,
      }, { onSuccess: onClose })}
    >
      <Stack>
        <Select label="Prescription" required value={prescription} onChange={setPrescription}
          data={(prescriptions.data ?? []).map((p) => ({
            value: String(p.id), label: `${p.medicine} (${p.visit_date})`,
          }))}
          nothingFoundMessage="No prescription is recorded for you" />
        <TextInput label="Medical expense date" type="date" required value={expenseDate}
          onChange={(e) => setExpenseDate(e.currentTarget.value)} />
        <TextInput label="Amount (₹)" required inputMode="decimal" value={amount}
          onChange={(e) => setAmount(e.currentTarget.value)} />
        <TextInput label="Description" value={description}
          onChange={(e) => setDescription(e.currentTarget.value)} />
      </Stack>
    </FormModal>
  );
}

export default function ClaimsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useClaims();
  const transition = useClaimTransition();
  const [creating, setCreating] = useState(false);
  const rows = data?.results ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="Medical bill reimbursement"
        subtitle={can("phc.claim.create") ? "Your claims and where each one is"
          : "Claims waiting on your office"}
        action={can("phc.claim.create") && (
          <Button onClick={() => setCreating(true)}>New claim</Button>
        )}
      />
      {transition.error != null && <Text c="red" mb="sm">{errorMessage(transition.error)}</Text>}
      <ListStates isPending={isPending} error={error} empty={rows.length === 0}
        emptyText="No reimbursement claims" />
      <Stack>
        {rows.map((c) => (
          <Card key={c.id} withBorder padding="lg">
            <Group justify="space-between">
              <div>
                <Text fw={700}>Claim #{c.id} · ₹{c.amount}</Text>
                <Text size="sm" c="dimmed">
                  {c.prescription_label} · expense on {c.expense_date}
                </Text>
              </div>
              <Badge variant="light">{c.status_label}</Badge>
            </Group>
            <Timeline mt="sm" bulletSize={12} lineWidth={2}>
              {c.actions.map((a) => (
                <Timeline.Item key={`${a.event}-${a.created_at}`} title={a.event}>
                  <Text size="xs" c="dimmed">{new Date(a.created_at).toLocaleString()}</Text>
                </Timeline.Item>
              ))}
            </Timeline>
            {c.allowed_events.length > 0 && (
              <Group mt="sm" gap="xs">
                {c.allowed_events.map((event) => (
                  <Button key={event} size="xs" color={event === "reject" ? "red" : undefined}
                    loading={transition.isPending}
                    onClick={() => transition.mutate({ id: c.id, event, note: "" })}>
                    {EVENT_LABELS[event] ?? event}
                  </Button>
                ))}
              </Group>
            )}
          </Card>
        ))}
      </Stack>
      {creating && <SubmitClaimModal onClose={() => setCreating(false)} />}
    </Container>
  );
}
