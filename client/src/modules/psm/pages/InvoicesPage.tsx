// Three-way invoice verification, mismatch holds, and vendor payments (PSM-UC-013, PSM-UC-029).
import { useState } from "react";
import { Badge, Button, Card, Container, Group, NumberInput, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateInvoice, useInvoiceAction, useInvoices } from "../api/hooks";
import type { Invoice } from "../api/types";

export default function InvoicesPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useInvoices();
  const createInv = useCreateInvoice();
  const act = useInvoiceAction();

  const [creating, setCreating] = useState(false);
  const [poId, setPoId] = useState<number | string>(1);
  const [invNum, setInvNum] = useState("");
  const [qty, setQty] = useState<number | string>(1);
  const [amount, setAmount] = useState("1000.00");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Invoices & Payments"
        subtitle="Three-way PO-GRN-Invoice matching, holds, and vendor payment release"
        action={can("psm.invoice.create") ? <Button onClick={() => setCreating(true)}>Record invoice</Button> : undefined}
      />

      <Card padding="lg">
        <DataTable<Invoice>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No invoices recorded." }}
          columns={[
            {
              key: "invoice",
              header: "Invoice",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.invoice_number}</Text>
                  <Text size="xs" c="dimmed">{r.po_number} · {r.vendor_name}</Text>
                </Stack>
              ),
            },
            { key: "billed", header: "Billed / Eligible", render: (r) => `₹${r.billed_amount} / ₹${r.eligible_amount}` },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Stack gap={2}>
                  <Badge color={r.status === "paid" ? "green" : r.status === "on_hold" ? "red" : "blue"} variant="light">
                    {r.status}
                  </Badge>
                  {r.hold_reason && <Text size="xs" c="red">{r.hold_reason}</Text>}
                </Stack>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {can("psm.invoice.review") && (r.status === "submitted" || r.status === "on_hold") && (
                    <Button
                      size="xs"
                      onClick={() =>
                        act.mutate(
                          { id: r.id, action: "verify" },
                          {
                            onSuccess: () => notifications.show({ color: "green", title: "Checked", message: "Three-way match completed." }),
                            onError: (e) => notifications.show({ color: "red", title: "Error", message: errorMessage(e) }),
                          },
                        )
                      }
                    >
                      Verify match
                    </Button>
                  )}
                  {can("psm.payment.approve") && (r.status === "verified" || r.status === "partially_paid") && (
                    <Button
                      size="xs"
                      color="green"
                      onClick={() =>
                        act.mutate(
                          { id: r.id, action: "pay", body: { amount: r.eligible_amount } },
                          {
                            onSuccess: () => notifications.show({ color: "green", title: "Paid", message: "Payment released." }),
                            onError: (e) => notifications.show({ color: "red", title: "Payment refused", message: errorMessage(e) }),
                          },
                        )
                      }
                    >
                      Release payment
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
        title="Record Vendor Invoice"
        submitLabel="Save invoice"
        submitting={createInv.isPending}
        onSubmit={() =>
          createInv.mutate(
            { purchase_order_id: Number(poId), invoice_number: invNum, billed_quantity: Number(qty), billed_amount: amount },
            {
              onSuccess: () => {
                setCreating(false);
                setInvNum("");
                notifications.show({ color: "green", title: "Saved", message: "Invoice recorded." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <NumberInput label="Purchase Order ID" value={poId} onChange={setPoId} required />
          <TextInput label="Invoice number" value={invNum} onChange={(e) => setInvNum(e.currentTarget.value)} required />
          <NumberInput label="Billed quantity" min={1} value={qty} onChange={setQty} required />
          <TextInput label="Billed amount" value={amount} onChange={(e) => setAmount(e.currentTarget.value)} required />
        </Stack>
      </FormModal>
    </Container>
  );
}
