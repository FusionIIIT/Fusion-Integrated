import { useQuery } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import type { Column } from "../../../ui/components/DataTable";

interface LeaveBalance {
  employee_id: string;
  leave_type: string;
  balance: string; // Decimal serialized as string
  last_updated: string;
}

export default function BalancesPage() {
  const { data, error, isLoading } = useQuery<{
    results: LeaveBalance[];
    next: string | null;
    previous: string | null;
  }>({
    queryKey: ["leave-balances"],
    queryFn: async () => {
      const res = await http.get("/leave/balances/");
      return res.data;
    },
  });

  const columns: Column<LeaveBalance>[] = [
    { key: "employee_id", header: "Employee ID" },
    { key: "leave_type", header: "Leave Type" },
    { key: "balance", header: "Balance" },
    { key: "last_updated", header: "Last Updated" },
  ];

  const rows = data?.results ?? [];

  return (
    <>
      <PageHeader title="Leave Balances" />
      {error && <ErrorState error={error} />}
      <DataTable
        rows={rows}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => `${r.employee_id}-${r.leave_type}`}
        empty={{
          title: "No balances found",
          description: "You have no leave balances recorded.",
        }}
      />
    </>
  );
}
