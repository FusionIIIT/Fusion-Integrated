import { Button, Stack } from "@mantine/core";
import { FaCheck } from "react-icons/fa";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useDiscrepancies, useResolveDiscrepancy } from "../api/hooks";
import type { DiscrepancyReport } from "../api/types";

export default function DiscrepanciesPage() {
  const { data: reports = [], isLoading } = useDiscrepancies();
  const resolve = useResolveDiscrepancy();

  const handleResolve = async (id: number) => {
    await resolve.mutateAsync({ id, resolution_summary: "Resolved by store keeper and purchase officer." });
  };

  const columns: Column<DiscrepancyReport>[] = [
    { key: "discrepancy_code", header: "Report No." },
    { key: "grn", header: "GRN Ref", render: (r) => r.grn?.grn_number ?? r.grn_number ?? "—" },
    { key: "discrepancy_type", header: "Type" },
    { key: "details", header: "Details" },
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
        r.status === "OPEN_HOLD_PAYMENT" ? (
          <Button
            size="xs"
            color="teal"
            variant="light"
            leftSection={<FaCheck size={12} />}
            onClick={() => handleResolve(r.id)}
            loading={resolve.isPending}
          >
            Mark Resolved
          </Button>
        ) : null,
    },
  ];

  return (
    <Stack gap="lg">
      <PageHeader
        title="Discrepancy Reports & Payment Holds"
        subtitle="Manage shipment defects, damaged deliveries, and automatic invoice holds"
      />
      <DataTable
        rows={reports}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No active discrepancies",
          description: "Shipment issues and delivery defects flagged during inspection will appear here.",
        }}
      />
    </Stack>
  );
}
