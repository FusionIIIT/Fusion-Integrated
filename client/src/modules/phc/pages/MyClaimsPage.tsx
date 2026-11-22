import { useState } from "react";
import {
  Button, Card, Container, Group, NumberInput, Select, Stack, Text, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaReceipt } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useCreateClaim, useMyClaims, useMyPrescriptions } from "../api/hooks";
import type { ReimbursementClaim } from "../api/types";

export default function MyClaimsPage() {
  const { data, isPending, error } = useMyClaims();
  const { can } = useAuth();
  const [creating, setCreating] = useState(false);
  const canSubmit = can("phc.reimbursement.submit");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="My Reimbursement Claims"
        subtitle="Medical bills submitted for reimbursement, and where each one stands"
        action={canSubmit && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
            New claim
          </Button>
        )}
      />

      <Card padding="lg">
        <DataTable<ReimbursementClaim>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.claim_id}
          minWidth={980}
          columns={[
            { key: "claim_id", header: "Claim",
              render: (r) => <Text fw={600}>#{r.claim_id}</Text> },
            { key: "expense_date", header: "Expense date",
              render: (r) => new Date(r.expense_date).toLocaleDateString() },
            { key: "amount", header: "Amount", align: "right",
              render: (r) => <Text fw={600}>₹{r.amount}</Text> },
            { key: "state", header: "Status",
              render: (r) => <StatusBadge status={r.state} /> },
            { key: "stage_actor", header: "With",
              render: (r) => r.stage_actor || "—" },
            { key: "created_at", header: "Submitted",
              render: (r) => new Date(r.created_at).toLocaleDateString() },
          ]}
          empty={{
            icon: FaReceipt,
            title: "No claims yet",
            description: canSubmit
              ? "Submit a claim against one of your prescriptions to track it here."
              : "Claims you submit will appear here.",
          }}
        />
      </Card>

      {canSubmit && <ClaimModal opened={creating} onClose={() => setCreating(false)} />}
    </Container>
  );
}

function ClaimModal({ opened, onClose }: {
  opened: boolean;
  onClose: () => void;
}) {
  const prescriptions = useMyPrescriptions();
  const create = useCreateClaim();
  const [prescriptionId, setPrescriptionId] = useState<string | null>(null);
  const [expenseDate, setExpenseDate] = useState("");
  const [amount, setAmount] = useState<string | number>("");
  const [description, setDescription] = useState("");

  const options = (prescriptions.data?.results ?? []).map((p) => ({
    value: String(p.id),
    label: `${p.medicine} · ${new Date(p.created_at).toLocaleDateString()}`,
  }));

  if (prescriptions.error) {
    return <Container size="lg"><ErrorState error={prescriptions.error} /></Container>;
  }

  function submit() {
    create.mutate(
      {
        prescription_id: Number(prescriptionId),
        expense_date: expenseDate,
        amount: String(amount),
        description,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Claim submitted",
            message: "The claim is with the PHC office for review.",
          });
          setPrescriptionId(null);
          setExpenseDate("");
          setAmount("");
          setDescription("");
          onClose();
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not submit claim", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <FormModal
      opened={opened} onClose={onClose}
      title="Submit a reimbursement claim"
      subtitle="Link the bill to a prescription on your own record"
      onSubmit={submit}
      submitLabel="Submit claim" submitting={create.isPending}
      error={create.error}
      disabled={!prescriptionId || !expenseDate || Number(amount) <= 0}
      disabledReason="Choose a prescription, expense date and a positive amount."
    >
      <Stack gap="md">
        <Select
          label="Prescription" required searchable
          placeholder={prescriptions.isPending ? "Loading…" : "Select"}
          data={options} value={prescriptionId} onChange={setPrescriptionId}
        />
        <Group grow>
          <TextInput
            label="Expense date" type="date" required
            value={expenseDate}
            onChange={(e) => setExpenseDate(e.currentTarget.value)}
          />
          <NumberInput
            label="Amount" required min={0} decimalScale={2} hideControls
            value={amount} onChange={setAmount} prefix="₹"
          />
        </Group>
        <TextInput
          label="Description" value={description}
          onChange={(e) => setDescription(e.currentTarget.value)}
          placeholder="What the bill was for"
          maxLength={500}
        />
        <Text size="xs" c="dimmed">
          Bills must be submitted within 90 days. A reimbursement is a new claim
          for each bill — an existing claim is never edited.
        </Text>
      </Stack>
    </FormModal>
  );
}
