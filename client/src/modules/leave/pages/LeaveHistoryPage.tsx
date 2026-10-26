import { Badge, Card, Container } from "@mantine/core";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveRequests } from "../hooks/useLeaveRequests";
import type { LeaveStatus } from "../api/types";

const STATUS_COLORS: Record<LeaveStatus, string> = {
  draft: "gray",
  submitted: "blue",
  substitute_pending: "orange",
  unit_head_review: "violet",
  establishment_review: "cyan",
  final_sanction: "indigo",
  approved: "green",
  rejected: "red",
  withdrawn: "gray",
  cancelled: "gray",
  extension_requested: "orange",
  resumption_pending: "blue",
  resumed: "teal",
};

export default function LeaveHistoryPage() {
  const { data, isPending } = useLeaveRequests({});
  const leaveRequests = data ?? { results: [] };

  return (
    <Container size="xl">
      <PageHeader title="Leave History" subtitle="Complete history of your leave requests" />
      <Card padding="lg">
        <DataTable
          rows={leaveRequests.results}
          loading={isPending}
          minWidth={1000}
          rowKey={(row) => row.id}
          columns={[
            { key: "id", header: "#" },
            { key: "category", header: "Category" },
            {
              key: "start_date",
              header: "From",
              render: (r) => new Date(r.start_date).toLocaleDateString(),
            },
            {
              key: "end_date",
              header: "To",
              render: (r) => new Date(r.end_date).toLocaleDateString(),
            },
            { key: "total_days", header: "Days" },
            { key: "purpose", header: "Purpose" },
            { key: "station_leave", header: "Station Leave", render: (r) => r.station_leave ? "Yes" : "No" },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <Badge color={STATUS_COLORS[r.status as LeaveStatus] || "gray"} variant="light">
                  {r.status.replace("_", " ")}
                </Badge>
              ),
            },
            {
              key: "applied_at",
              header: "Applied",
              render: (r) => r.applied_at ? new Date(r.applied_at).toLocaleDateString() : "-",
            },
            {
              key: "approved_at",
              header: "Approved",
              render: (r) => r.approved_at ? new Date(r.approved_at).toLocaleDateString() : "-",
            },
          ]}
          empty={{ title: "No leave history", description: "You haven't applied for any leave yet." }}
        />
      </Card>
    </Container>
  );
}