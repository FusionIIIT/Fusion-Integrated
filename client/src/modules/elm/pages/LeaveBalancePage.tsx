import { Container } from "@mantine/core";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveTypes, useMyBalance } from "../api";
import type { LeaveBalance } from "../api";

export default function LeaveBalancePage() {
  const { data, isPending, error } = useMyBalance();
  const types = useLeaveTypes();

  if (error) {
    return <Container size="xl"><ErrorState error={error} /></Container>;
  }

  const columns = [
    { key: "leave_type", header: "Leave type", render: (r: LeaveBalance) => types.data?.find(t => t.id === r.leave_type)?.name || "#" + r.leave_type },
    { key: "year", header: "Year" },
    { key: "allotted", header: "Allotted" },
    { key: "used", header: "Used" },
    { key: "available", header: "Available" },
  ];

  return (
    <Container size="xl">
      <PageHeader title="Leave Balance" subtitle="Allotted, used and available days this year" />
      <DataTable<LeaveBalance>
        rows={data ?? []}
        loading={isPending}
        rowKey={r => r.id}
        columns={columns}
        empty={{ title: "No leave balance yet", description: "Your leave administrator has not allotted leave for this year." }}
      />
    </Container>
  );
}
