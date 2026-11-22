// Inter-departmental stock transfers (PSM-UC-021, 033, 034, BW-PSM-08).
import { useState } from "react";
import { Badge, Button, Card, Container, Group, NumberInput, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateTransfer, useTransferAction, useTransfers } from "../api/hooks";
import type { StockTransfer } from "../api/types";

export default function TransfersPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useTransfers();
  const createTrf = useCreateTransfer();
  const act = useTransferAction();

  const [creating, setCreating] = useState(false);
  const [itemId, setItemId] = useState<number | string>(1);
  const [srcId, setSrcId] = useState<number | string>(1);
  const [dstId, setDstId] = useState<number | string>(2);
  const [qty, setQty] = useState<number | string>(1);
  const [notes, setNotes] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Inter-Departmental Stock Transfers"
        subtitle="Request, dispatch, and confirm stock transfers between stores"
        action={can("psm.transfer.create") ? <Button onClick={() => setCreating(true)}>Request transfer</Button> : undefined}
      />

      <Card padding="lg">
        <DataTable<StockTransfer>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No stock transfers found in your scope." }}
          columns={[
            { key: "number", header: "Transfer", render: (r) => r.transfer_number },
            { key: "item", header: "Item", render: (r) => `${r.item_name} (${r.quantity})` },
            { key: "route", header: "Route", render: (r) => `${r.source_location_code} → ${r.destination_location_code}` },
            { key: "status", header: "Status", render: (r) => <Badge variant="light">{r.status}</Badge> },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {can("psm.transfer.update") && r.status === "requested" && (
                    <Button size="xs" onClick={() => act.mutate({ id: r.id, action: "dispatch" })}>Dispatch</Button>
                  )}
                  {can("psm.transfer.approve") && r.status === "dispatched" && (
                    <Button size="xs" color="green" onClick={() => act.mutate({ id: r.id, action: "confirm" })}>Confirm receipt</Button>
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
        title="Request Stock Transfer"
        submitLabel="Submit request"
        submitting={createTrf.isPending}
        onSubmit={() =>
          createTrf.mutate(
            { item_id: Number(itemId), source_location_id: Number(srcId), destination_location_id: Number(dstId), quantity: Number(qty), notes },
            {
              onSuccess: () => {
                setCreating(false);
                notifications.show({ color: "green", title: "Requested", message: "Transfer request created." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <NumberInput label="Item ID" value={itemId} onChange={setItemId} required />
          <NumberInput label="Source location ID" value={srcId} onChange={setSrcId} required />
          <NumberInput label="Destination location ID" value={dstId} onChange={setDstId} required />
          <NumberInput label="Quantity" min={1} value={qty} onChange={setQty} required />
          <TextInput label="Notes" value={notes} onChange={(e) => setNotes(e.currentTarget.value)} />
        </Stack>
      </FormModal>
    </Container>
  );
}
