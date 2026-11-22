// Stock availability, adjustments, and internal stock issues (PSM-UC-007, 008, 009, 017).
import { useState } from "react";
import { Badge, Button, Card, Container, Group, NumberInput, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateStockItem, useInternalIssueAction, useInternalIssues, useRecordStockAdjustment, useStockAvailability,
} from "../api/hooks";
import type { InternalIssue, StockAvailability } from "../api/types";

export default function StockPage() {
  const { can } = useAuth();
  const avail = useStockAvailability();
  const issues = useInternalIssues();
  const createItem = useCreateStockItem();
  const adjust = useRecordStockAdjustment();
  const issueAct = useInternalIssueAction();

  const [addingItem, setAddingItem] = useState(false);
  const [adjusting, setAdjusting] = useState(false);
  const [sku, setSku] = useState("");
  const [itemName, setItemName] = useState("");
  const [itemId, setItemId] = useState<number | string>(1);
  const [locationId, setLocationId] = useState<number | string>(1);
  const [delta, setDelta] = useState<number | string>(1);
  const [reason, setReason] = useState("");

  if (avail.error) return <Container size="xl"><ErrorState error={avail.error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Stock & Internal Issues"
        subtitle="Departmental and central stock balances, adjustments, and dispatch"
        action={
          can("psm.stock.update") ? (
            <Group gap="xs">
              <Button variant="light" onClick={() => setAddingItem(true)}>Add stock item</Button>
              <Button onClick={() => setAdjusting(true)}>Record adjustment</Button>
            </Group>
          ) : undefined
        }
      />

      <Stack gap="lg">
        <Card padding="lg">
          <Title order={4} mb="sm">Stock Availability</Title>
          <DataTable<StockAvailability>
            rows={avail.data?.results ?? []}
            loading={avail.isPending}
            rowKey={(r) => `${r.item_id}-${r.location_id}`}
            empty={{ title: "No stock balances recorded in your scope." }}
            columns={[
              { key: "sku", header: "SKU", render: (r) => r.sku },
              { key: "item_name", header: "Item", render: (r) => r.item_name },
              { key: "location", header: "Location", render: (r) => `${r.location_code} (${r.department})` },
              { key: "on_hand", header: "On Hand", render: (r) => r.on_hand },
              { key: "reserved", header: "Reserved", render: (r) => r.reserved },
              { key: "allocable", header: "Allocable", render: (r) => <Badge color="teal">{r.allocable}</Badge> },
            ]}
          />
        </Card>

        <Card padding="lg">
          <Title order={4} mb="sm">Internal Stock Issues</Title>
          {issues.error ? (
            <ErrorState error={issues.error} />
          ) : (
            <DataTable<InternalIssue>
            rows={issues.data?.results ?? []}
            loading={issues.isPending}
            rowKey={(r) => r.id}
            empty={{ title: "No internal stock issues found." }}
            columns={[
              { key: "indent", header: "Indent", render: (r) => r.indent_number ?? `#${r.indent_id}` },
              { key: "item", header: "Item", render: (r) => `${r.item_description} (${r.quantity})` },
              { key: "location", header: "Location", render: (r) => r.location_code },
              { key: "status", header: "Status", render: (r) => <Badge variant="light">{r.status}</Badge> },
              {
                key: "actions",
                header: "Actions",
                align: "right",
                render: (r) =>
                  can("psm.stock.update") && (r.status === "approved" || r.status === "picking_scheduled") ? (
                    <Button
                      size="xs"
                      onClick={() =>
                        issueAct.mutate(
                          { id: r.id, action: "dispatch" },
                          {
                            onSuccess: () => notifications.show({ color: "green", title: "Dispatched", message: "Internal issue dispatched." }),
                            onError: (e) => notifications.show({ color: "red", title: "Failed", message: errorMessage(e) }),
                          },
                        )
                      }
                    >
                      Dispatch
                    </Button>
                  ) : (
                    <Text size="xs" c="dimmed">—</Text>
                  ),
              },
            ]}
          />
          )}
        </Card>
      </Stack>

      <FormModal
        opened={addingItem}
        onClose={() => setAddingItem(false)}
        title="Add Stock Item"
        submitLabel="Create item"
        submitting={createItem.isPending}
        onSubmit={() =>
          createItem.mutate(
            { sku, name: itemName },
            {
              onSuccess: () => {
                setAddingItem(false);
                setSku("");
                setItemName("");
                notifications.show({ color: "green", title: "Created", message: "Stock item added." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Failed", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <TextInput label="SKU" value={sku} onChange={(e) => setSku(e.currentTarget.value)} required />
          <TextInput label="Item name" value={itemName} onChange={(e) => setItemName(e.currentTarget.value)} required />
        </Stack>
      </FormModal>

      <FormModal
        opened={adjusting}
        onClose={() => setAdjusting(false)}
        title="Record Stock Adjustment"
        submitLabel="Post adjustment"
        submitting={adjust.isPending}
        onSubmit={() =>
          adjust.mutate(
            { item_id: Number(itemId), location_id: Number(locationId), quantity_delta: Number(delta), reason },
            {
              onSuccess: () => {
                setAdjusting(false);
                setReason("");
                notifications.show({ color: "green", title: "Posted", message: "Stock ledger updated." });
              },
              onError: (e) => notifications.show({ color: "red", title: "Refused", message: errorMessage(e) }),
            },
          )
        }
      >
        <Stack gap="sm">
          <NumberInput label="Item ID" value={itemId} onChange={setItemId} required />
          <NumberInput label="Location ID" value={locationId} onChange={setLocationId} required />
          <NumberInput label="Quantity delta" value={delta} onChange={setDelta} required />
          <TextInput label="Adjustment reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} required />
        </Stack>
      </FormModal>
    </Container>
  );
}
