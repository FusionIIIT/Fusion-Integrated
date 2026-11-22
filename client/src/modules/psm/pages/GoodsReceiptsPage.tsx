import { Button, Stack } from "@mantine/core";
import { FaCheckCircle } from "react-icons/fa";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAcknowledgeGoodsReceipt, useGoodsReceipts } from "../api/hooks";
import type { GoodsReceiptNote } from "../api/types";

export default function GoodsReceiptsPage() {
  const { data: grns = [], isLoading } = useGoodsReceipts();
  const ackGRN = useAcknowledgeGoodsReceipt();

  const handleAcknowledge = async (id: number) => {
    await ackGRN.mutateAsync(id);
  };

  const columns: Column<GoodsReceiptNote>[] = [
    { key: "grn_number", header: "GRN Number" },
    { key: "po_number", header: "PO Reference", render: (r) => r.purchase_order?.po_number ?? "N/A" },
    { key: "receipt_date", header: "Receipt Date" },
    { key: "challan_number", header: "Challan / Inv", render: (r) => r.challan_number || r.invoice_number || "—" },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status.toLowerCase()} />,
    },
    {
      key: "ack",
      header: "Indentor Ack",
      render: (r) => (r.indentor_acknowledged ? "Acknowledged" : "Pending"),
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: (r) =>
        !r.indentor_acknowledged && r.status === "ACCEPTED" ? (
          <Button
            size="xs"
            color="green"
            variant="light"
            leftSection={<FaCheckCircle size={12} />}
            onClick={() => handleAcknowledge(r.id)}
            loading={ackGRN.isPending}
          >
            Acknowledge Receipt
          </Button>
        ) : null,
    },
  ];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Goods Receipt Notes (GRN)"
        subtitle="Inspection, verification, and end-user acknowledgement of delivered store items"
      />
      <DataTable
        rows={grns}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No goods receipt notes logged",
          description: "GRN entries will appear here when storekeepers inspect incoming vendor deliveries.",
        }}
      />
    </Stack>
  );
}
