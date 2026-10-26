import { useState } from "react";
import { Badge, Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePendingApprovals, useUnitHeadReview, useEstablishmentReview, useFinalSanction } from "../hooks/useLeaveRequests";
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

export default function PendingApprovalsPage() {
  const notify = notifications;
  const [filters, setFilters] = useState({ status: "", category: "" });
  const { data, isPending, refetch } = usePendingApprovals(filters);
  const leaveRequests = data ?? { results: [] };
  const unitHeadReview = useUnitHeadReview();
  const establishmentReview = useEstablishmentReview();
  const finalSanction = useFinalSanction();

  const handleUnitHeadReview = async (id: number, recommend: boolean) => {
    const remark = window.prompt("Enter remark (optional):") || "";
    try {
      await unitHeadReview.mutateAsync({ id, body: { recommend, remark } });
      notify.show({ title: "Success", message: recommend ? "Recommended" : "Not Recommended", color: "green" });
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to review", color: "red" });
    }
  };

  const handleEstablishmentReview = async (id: number, action: "forward" | "return") => {
    const remark = window.prompt("Enter remark (optional):") || "";
    try {
      await establishmentReview.mutateAsync({ id, body: { action, remark } });
      notify.show({ title: "Success", message: action === "forward" ? "Forwarded to Final Authority" : "Returned to Unit Head", color: "green" });
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to review", color: "red" });
    }
  };

  const handleFinalSanction = async (id: number, approve: boolean) => {
    const remark = window.prompt("Enter remark (optional):") || "";
    try {
      await finalSanction.mutateAsync({ id, body: { approve, remark } });
      notify.show({ title: "Success", message: approve ? "Approved" : "Rejected", color: "green" });
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to sanction", color: "red" });
    }
  };

  const getActions = (status: LeaveStatus, id: number) => {
    switch (status) {
      case "unit_head_review":
        return (
          <Group>
            <Button size="sm" color="green" onClick={() => handleUnitHeadReview(id, true)}>Recommend</Button>
            <Button size="sm" color="red" onClick={() => handleUnitHeadReview(id, false)}>Not Recommend</Button>
          </Group>
        );
      case "establishment_review":
        return (
          <Group>
            <Button size="sm" color="blue" onClick={() => handleEstablishmentReview(id, "forward")}>Forward</Button>
            <Button size="sm" color="orange" onClick={() => handleEstablishmentReview(id, "return")}>Return</Button>
          </Group>
        );
      case "final_sanction":
        return (
          <Group>
            <Button size="sm" color="green" onClick={() => handleFinalSanction(id, true)}>Approve</Button>
            <Button size="sm" color="red" onClick={() => handleFinalSanction(id, false)}>Reject</Button>
          </Group>
        );
      default:
        return null;
    }
  };

  return (
    <Container size="xl">
      <PageHeader title="Pending Approvals" subtitle="Leave requests awaiting your review" />
      <Card padding="lg">
        <Group gap="md" mb="md" wrap="wrap">
          <select
            value={filters.status}
            onChange={(e) => setFilters((p) => ({ ...p, status: e.target.value }))}
            className="mantine-Input-input"
            style={{ minWidth: 200 }}
          >
            <option value="">All Statuses</option>
            <option value="submitted">Submitted</option>
            <option value="substitute_pending">Substitute Pending</option>
            <option value="unit_head_review">Unit Head Review</option>
            <option value="establishment_review">Establishment Review</option>
            <option value="final_sanction">Final Sanction</option>
          </select>
        </Group>
        <DataTable
          rows={leaveRequests.results}
          loading={isPending}
          minWidth={1000}
          rowKey={(row) => row.id}
          columns={[
            { key: "id", header: "#" },
            { key: "user_id", header: "Employee ID" },
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
              key: "actions",
              header: "Actions",
              render: (r) => getActions(r.status as LeaveStatus, r.id),
            },
          ]}
          empty={{ title: "No pending approvals", description: "All caught up!" }}
        />
      </Card>
    </Container>
  );
}