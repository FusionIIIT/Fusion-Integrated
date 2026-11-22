// Goods Receipt Notes, delivery confirmation, and discrepancy resolution (PSM-UC-002, 020, 028, 032).
import { useState } from "react";
import { Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Text, Textarea, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useConfirmGrn, useCreateDiscrepancy, useCreateGrn, useDiscrepancies, useGrns, useResolveDiscrepancy,
} from "../api/hooks";
import type { DiscrepancyCase, GoodsReceiptNote } from "../api/types";

export default function ReceiptsPage() {
  const { can } = useAuth();
  const grns = useGrns();
  const cases = useDiscrepancies();
  const createGrn = useCreateGrn();
  const confirmGrn = useConfirmGrn();
  const createDisc = useCreateDiscrepancy();
  const resolveDisc = useResolveDiscrepancy();

  const [recording, setRecording] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [poId, setPoId] = useState<number | string>(1);
  const [receivedQty, setReceivedQty] = useState<number | string>(1);
  const [acceptedQty, setAcceptedQty] = useState<number | string>(1);
  const [rejectedQty, setRejectedQty] = useState<number | string>(0);

  const [discGrnId, setDiscGrnId] = useState<number | string>(1);
  const [discType, setDiscType] = useState("damage");
  const [discQty, setDiscQty] = useState<number | string>(1);
  const [discDesc, setDiscDesc] = useState("");
  const [discRes, setDiscRes] = useState("return");

  if (grns.error) return <Container size="xl"><ErrorState error={grns.error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Receipts & Discrepancies"
        subtitle="Inspect deliveries, confirm receipts, and resolve delivery discrepancies"
        action={
          can("psm.grn.create") ? (
            <Group gap="xs">
              <Button variant="light" onClick={() => setReporting(true)}>Report discrepancy</Button>
              <Button onClick={() => setRecording(true)}>Record GRN</Button>
            </Group>
          ) : undefined
        }
      />

      <Stack gap="lg">
        <Card padding="lg">
          <Title order={4} mb="sm">Goods Receipt Notes</Title>
          <DataTable<GoodsReceiptNote>
            rows={grns.data?.results ?? []}
            loading={grns.isPending}
            rowKey={(r) => r.id}
            empty={{ title: "No goods receipt notes recorded yet." }}
            columns={[
              { key: "grn", header: "GRN", render: (r) => r.grn_number },
              { key: "qty", header: "Received / Accepted / Rejected", render: (r) => `${r.received_quantity} / ${r.accepted_quantity} / ${r.rejected_quantity}` },
              { key: "status", header: "Status", render: (r) => <Badge variant="light">{r.status}</Badge> },
              { key: "posted", header: "Stock Posted", render: (r) => (r.stock_posted ? "Yes" : "No") },
              {
                key: "actions",
                header: "Actions",
                align: "right",
                render: (r) =>
                  can("psm.grn.approve") && !r.stock_posted && r.accepted_quantity > 0 ? (
                    <Button
                      size="xs"
                      color="green"
                      onClick={() =>
                        confirmGrn.mutate(r.id, {
                          onSuccess: () => notifications.show({ color: "green", title: "Confirmed", message: "Receipt confirmed and stock posted." }),
                          onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
                        })
                      }
                    >
                      Confirm receipt
                    </Button>
                  ) : (
                    <Text size="xs" c="dimmed">—</Text>
                  ),
              },
            ]}
          />
        </Card>

        <Card padding="lg">
          <Title order={4} mb="sm">Discrepancy Cases</Title>
          <DataTable<DiscrepancyCase>
            rows={cases.data?.results ?? []}
            loading={cases.isPending}
            rowKey={(r) => r.id}
            empty={{ title: "No discrepancy cases logged." }}
            columns={[
              { key: "case", header: "Case", render: (r) => r.case_number },
              { key: "type", header: "Type", render: (r) => `${r.discrepancy_type} (${r.affected_quantity})` },
              { key: "res", header: "Requested", render: (r) => r.requested_resolution },
              { key: "status", header: "Status", render: (r) => <Badge variant="light">{r.status}</Badge> },
              {
                key: "actions",
                header: "Actions",
                align: "right",
                render: (r) =>
                  can("psm.discrepancy.update") && r.status === "open" ? (
                    <Button
                      size="xs"
                      onClick={() =>
                        resolveDisc.mutate({
                          id: r.id,
                          body: { resolution_action: "resolve", resolution_notes: "Resolved via return/adjustment", inventory_adjusted: true, accounting_adjusted: true },
                        })
                      }
                    >
                      Resolve
                    </Button>
                  ) : (
                    <Text size="xs" c="dimmed">—</Text>
                  ),
              },
            ]}
          />
        </Card>
      </Stack>

      <FormModal
        opened={recording}
        onClose={() => setRecording(false)}
        title="Record Goods Receipt Note"
        submitLabel="Save GRN"
        submitting={createGrn.isPending}
        onSubmit={() =>
          createGrn.mutate(
            {
              purchase_order_id: Number(poId),
              received_quantity: Number(receivedQty),
              accepted_quantity: Number(acceptedQty),
              rejected_quantity: Number(rejectedQty),
            },
            {
              onSuccess: () => {
                setRecording(false);
                notifications.show({ color: "green", title: "GRN saved", message: "Delivery inspection recorded." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <NumberInput label="Purchase Order ID" value={poId} onChange={setPoId} required />
          <NumberInput label="Received quantity" min={1} value={receivedQty} onChange={setReceivedQty} required />
          <NumberInput label="Accepted quantity" min={0} value={acceptedQty} onChange={setAcceptedQty} required />
          <NumberInput label="Rejected quantity" min={0} value={rejectedQty} onChange={setRejectedQty} required />
        </Stack>
      </FormModal>

      <FormModal
        opened={reporting}
        onClose={() => setReporting(false)}
        title="Report Delivery Discrepancy"
        submitLabel="Log discrepancy"
        submitting={createDisc.isPending}
        onSubmit={() =>
          createDisc.mutate(
            {
              grn_id: Number(discGrnId),
              discrepancy_type: discType,
              affected_quantity: Number(discQty),
              description: discDesc,
              requested_resolution: discRes,
            },
            {
              onSuccess: () => {
                setReporting(false);
                setDiscDesc("");
                notifications.show({ color: "green", title: "Logged", message: "Discrepancy case opened." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <NumberInput label="GRN ID" value={discGrnId} onChange={setDiscGrnId} required />
          <Select label="Discrepancy type" data={["damage", "shortage", "wrong_item", "quality_defect"]} value={discType} onChange={(v) => setDiscType(v ?? "damage")} />
          <NumberInput label="Affected quantity" min={1} value={discQty} onChange={setDiscQty} required />
          <Select label="Requested resolution" data={["return", "replacement", "warranty", "adjustment"]} value={discRes} onChange={(v) => setDiscRes(v ?? "return")} />
          <Textarea label="Description" value={discDesc} onChange={(e) => setDiscDesc(e.currentTarget.value)} required />
        </Stack>
      </FormModal>
    </Container>
  );
}
