// Purchase orders issuance and delivery schedule tracking (PSM-UC-026, PSM-UC-027).
import { useState } from "react";
import { Badge, Button, Card, Container, NumberInput, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreatePurchaseOrder, usePurchaseOrders, useUpdatePurchaseOrder } from "../api/hooks";
import type { PurchaseOrder } from "../api/types";

export default function PurchaseOrdersPage() {
  const { can } = useAuth();
  const { data, isPending, error } = usePurchaseOrders();
  const createPo = useCreatePurchaseOrder();
  const updatePo = useUpdatePurchaseOrder();

  const [creating, setCreating] = useState(false);
  const [indentId, setIndentId] = useState<number | string>(1);
  const [vendorId, setVendorId] = useState<number | string>(1);
  const [unitPrice, setUnitPrice] = useState("1000.00");
  const [deliveryDate, setDeliveryDate] = useState("2026-12-31");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Purchase Orders"
        subtitle="Issue purchase orders and track planned and actual delivery schedules"
        action={can("psm.purchase_order.create") ? <Button onClick={() => setCreating(true)}>Issue PO</Button> : undefined}
      />

      <Card padding="lg">
        <DataTable<PurchaseOrder>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{ title: "No purchase orders found in your scope." }}
          columns={[
            {
              key: "po_number",
              header: "PO",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.po_number}</Text>
                  <Text size="xs" c="dimmed">{r.vendor_name}</Text>
                </Stack>
              ),
            },
            { key: "qty", header: "Qty / Total", render: (r) => `${r.ordered_quantity} · ₹${r.total_amount}` },
            { key: "delivery", header: "Planned Delivery", render: (r) => r.planned_delivery_date },
            { key: "status", header: "Status", render: (r) => <Badge variant="light">{r.status}</Badge> },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) =>
                can("psm.purchase_order.update") && r.status === "issued" ? (
                  <Button
                    size="xs"
                    onClick={() =>
                      updatePo.mutate(
                        { id: r.id, body: { status: "in_transit" } },
                        {
                          onSuccess: () => notifications.show({ color: "green", title: "Updated", message: `${r.po_number} marked in transit.` }),
                          onError: (e) => notifications.show({ color: "red", title: "Failed", message: errorMessage(e) }),
                        },
                      )
                    }
                  >
                    Mark in transit
                  </Button>
                ) : (
                  <Text size="xs" c="dimmed">—</Text>
                ),
            },
          ]}
        />
      </Card>

      <FormModal
        opened={creating}
        onClose={() => setCreating(false)}
        title="Issue Purchase Order"
        submitLabel="Issue PO"
        submitting={createPo.isPending}
        onSubmit={() =>
          createPo.mutate(
            { indent_id: Number(indentId), vendor_id: Number(vendorId), unit_price: unitPrice, planned_delivery_date: deliveryDate },
            {
              onSuccess: () => {
                setCreating(false);
                notifications.show({ color: "green", title: "PO issued", message: "Purchase order created." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <NumberInput label="Indent ID" value={indentId} onChange={setIndentId} required />
          <NumberInput label="Vendor ID" value={vendorId} onChange={setVendorId} required />
          <TextInput label="Unit price" value={unitPrice} onChange={(e) => setUnitPrice(e.currentTarget.value)} required />
          <TextInput label="Planned delivery date (YYYY-MM-DD)" value={deliveryDate} onChange={(e) => setDeliveryDate(e.currentTarget.value)} required />
        </Stack>
      </FormModal>
    </Container>
  );
}
