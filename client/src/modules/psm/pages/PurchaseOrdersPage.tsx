import { Button, Stack } from "@mantine/core";
import { FaPaperPlane } from "react-icons/fa";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useIssuePurchaseOrder, usePurchaseOrders } from "../api/hooks";
import type { PurchaseOrder } from "../api/types";

export default function PurchaseOrdersPage() {
  const { data: pos = [], isLoading } = usePurchaseOrders();
  const issuePO = useIssuePurchaseOrder();

  const handleIssue = async (id: number) => {
    await issuePO.mutateAsync(id);
  };

  const columns: Column<PurchaseOrder>[] = [
    { key: "po_number", header: "PO Number" },
    { key: "vendor", header: "Vendor", render: (r) => r.vendor?.name ?? "N/A" },
    { key: "procurement_method", header: "Procurement Method" },
    {
      key: "total_amount",
      header: "Total (₹)",
      align: "right",
      render: (r) => `₹${Number(r.total_amount).toLocaleString("en-IN")}`,
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status.toLowerCase()} />,
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: (r) =>
        r.status === "DRAFT" ? (
          <Button
            size="xs"
            color="blue"
            leftSection={<FaPaperPlane size={12} />}
            onClick={() => handleIssue(r.id)}
            loading={issuePO.isPending}
          >
            Issue PO
          </Button>
        ) : null,
    },
  ];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Purchase Orders"
        subtitle="Manage vendor purchase orders, execution methods, and delivery progress"
      />
      <DataTable
        rows={pos}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No purchase orders generated",
          description: "Purchase orders appear here once approved indents are converted for procurement.",
        }}
      />
    </Stack>
  );
}
