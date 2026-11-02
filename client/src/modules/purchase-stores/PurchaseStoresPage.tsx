import {
  Alert, Button, Container, Group, Modal, NumberInput, Select, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { FaBoxes, FaFileInvoice, FaSync } from "react-icons/fa";

import { http } from "../../lib/http";
import { DataTable, type Column } from "../../ui/components/DataTable";
import { ErrorState } from "../../ui/components/ErrorState";
import { PageHeader } from "../../ui/components/PageHeader";

type Area = "indents" | "stock" | "procurement";
type Row = Record<string, unknown> & { id: number };

const config: Record<Area, { title: string; endpoint: string; icon: typeof FaBoxes }> = {
  indents: { title: "Purchase Indents", endpoint: "/purchase-stores/indents", icon: FaFileInvoice },
  stock: { title: "Stock and Transfers", endpoint: "/purchase-stores/stock", icon: FaBoxes },
  procurement: { title: "Procurement", endpoint: "/purchase-stores/purchase-orders", icon: FaFileInvoice },
};

function columnsFor(area: Area): Column<Row>[] {
  const keys: Record<Area, string[]> = {
    indents: ["reference", "department_id", "status", "priority", "created_at"],
    stock: ["sku", "item_name", "department_id", "quantity_on_hand", "quantity_reserved", "quantity_available"],
    procurement: ["reference", "indent_id", "vendor_id", "status", "total_amount", "planned_delivery_at"],
  };
  return keys[area].map((key) => ({
    key,
    header: key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()),
  }));
}

export default function PurchaseStoresPage({ area }: { area: Area }) {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [departmentId, setDepartmentId] = useState<number | "">("");
  const [itemName, setItemName] = useState("");
  const [quantity, setQuantity] = useState<number | "">(1);
  const [unitCost, setUnitCost] = useState<number | "">(0);
  const [justification, setJustification] = useState("");
  const [sku, setSku] = useState("");
  const client = useQueryClient();
  const { title, endpoint, icon: Icon } = config[area];
  const query = useQuery({
    queryKey: ["purchase-stores", area, statusFilter],
    queryFn: async () => {
      const response = await http.get<Row[]>(endpoint, {
        params: area === "indents" && statusFilter ? { status: statusFilter } : undefined,
      });
      return response.data;
    },
  });
  const submitIndent = useMutation({
    mutationFn: async () => (await http.post<Row>("/purchase-stores/indents", {
      department_id: departmentId,
      justification,
      lines: [{ item_name: itemName, quantity, estimated_unit_cost: unitCost, sku }],
    })).data,
    onSuccess: async () => {
      setCreateOpen(false);
      setDepartmentId("");
      setItemName("");
      setQuantity(1);
      setUnitCost(0);
      setJustification("");
      setSku("");
      await client.invalidateQueries({ queryKey: ["purchase-stores", "indents"] });
    },
  });

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title={title}
        subtitle="Purchase, procurement and stores lifecycle"
        action={(
          <Group>
            {area === "indents" && <Button onClick={() => setCreateOpen(true)}>New indent</Button>}
            <Button variant="light" leftSection={<FaSync size={14} />} onClick={() => void query.refetch()}>
              Refresh
            </Button>
          </Group>
        )}
      />
      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="Create purchase indent">
        <Stack>
          <NumberInput label="Department ID" min={1} value={departmentId} onChange={(value) => setDepartmentId(typeof value === "number" ? value : "")} required />
          <TextInput label="Item" value={itemName} onChange={(event) => setItemName(event.currentTarget.value)} required />
          <TextInput label="SKU (for stock lookup)" value={sku} onChange={(event) => setSku(event.currentTarget.value)} />
          <NumberInput label="Quantity" min={0.001} decimalScale={3} value={quantity} onChange={(value) => setQuantity(typeof value === "number" ? value : "")} required />
          <NumberInput label="Estimated unit cost" min={0} decimalScale={2} value={unitCost} onChange={(value) => setUnitCost(typeof value === "number" ? value : "")} required />
          <Textarea label="Justification" value={justification} onChange={(event) => setJustification(event.currentTarget.value)} required />
          {submitIndent.isError && <ErrorState error={submitIndent.error} />}
          <Button
            loading={submitIndent.isPending}
            disabled={!departmentId || !itemName.trim() || !justification.trim() || quantity === "" || unitCost === ""}
            onClick={() => submitIndent.mutate()}
          >
            Submit indent
          </Button>
        </Stack>
      </Modal>
      <Stack gap="md">
        {area === "indents" && (
          <Select
            clearable
            label="Filter by status"
            placeholder="All statuses"
            value={statusFilter}
            onChange={setStatusFilter}
            data={[
              "DRAFT", "SUBMITTED", "STOCK_RESERVED", "EXTERNAL_PROCUREMENT_REQUIRED",
              "DEPARTMENT_REVIEWED", "AWAITING_FINAL_APPROVAL", "PROCUREMENT_AUTHORIZED",
              "PO_ISSUED", "DELIVERED", "RECEIPT_CONFIRMED", "REJECTED", "WITHDRAWN",
            ]}
          />
        )}
        {query.isError && <ErrorState error={query.error} />}
        {area === "stock" && !query.isError && !query.isLoading && query.data?.length === 0 && (
          <Alert icon={<Icon />} color="blue" title="No stock records">
            Stock balances will appear here when a receipt or stock adjustment is posted.
          </Alert>
        )}
        <DataTable
          rows={query.data ?? []}
          columns={columnsFor(area)}
          loading={query.isLoading}
          rowKey={(row) => row.id}
          empty={{
            icon: Icon,
            title: area === "indents" ? "No purchase indents" : area === "stock" ? "No stock records" : "No purchase orders",
            description: area === "indents" ? "Submitted and draft indents will appear here." : "Records appear here as the procurement lifecycle progresses.",
          }}
        />
        {query.data && <Group justify="flex-end"><Text size="xs" c="dimmed">{query.data.length} records</Text></Group>}
      </Stack>
    </Container>
  );
}
