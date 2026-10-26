import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveRequests, useWithdrawLeaveRequest, useCancelLeaveRequest, useExtendLeaveRequest, useResumeLeaveRequest } from "../hooks/useLeaveRequests";
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

export default function MyLeaveRequestsPage() {
  const notify = notifications;
  const [filters, setFilters] = useState({ status: "", category: "" });
  const { data, isPending, refetch } = useLeaveRequests(filters);
  const leaveRequests = data ?? { results: [] };
  const withdrawLeave = useWithdrawLeaveRequest();
  const cancelLeave = useCancelLeaveRequest();
  const extendLeave = useExtendLeaveRequest();
  const resumeLeave = useResumeLeaveRequest();

  const handleWithdraw = async (id: number) => {
    if (!window.confirm("Withdraw this leave request?")) return;
    try {
      await withdrawLeave.mutateAsync({ id, body: { reason: "Withdrawn by employee" } });
      notify.show({ title: "Withdrawn", message: "Leave request withdrawn", color: "green" });
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to withdraw", color: "red" });
    }
  };

  const handleCancel = async (id: number) => {
    if (!window.confirm("Cancel this approved leave?")) return;
    try {
      await cancelLeave.mutateAsync({ id, body: { reason: "Cancelled by employee" } });
      notify.show({ title: "Cancelled", message: "Leave cancelled", color: "green" });
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to cancel", color: "red" });
    }
  };

  const handleExtend = async (id: number) => {
    const newEndDate = window.prompt("Enter new end date (YYYY-MM-DD):");
    if (!newEndDate) return;
    const purpose = window.prompt("Enter extension reason:");
    if (!purpose) return;
    try {
      await extendLeave.mutateAsync({ id, body: { end_date: newEndDate, purpose } });
      notify.show({ title: "Extended", message: "Leave extension submitted", color: "green" });
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to extend", color: "red" });
    }
  };

  const handleResume = async (id: number) => {
    const resumptionDate = window.prompt("Enter resumption date (YYYY-MM-DD):");
    if (!resumptionDate) return;
    try {
      await resumeLeave.mutateAsync({ id, body: { resumption_date: resumptionDate } });
      notify.show({ title: "Resumption Submitted", message: "Resumption of duty submitted", color: "green" });
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to submit resumption", color: "red" });
    }
  };

  const canWithdraw = (status: LeaveStatus) => ["submitted", "substitute_pending", "unit_head_review"].includes(status);
  const canCancel = (status: LeaveStatus) => status === "approved";
  const canExtend = (status: LeaveStatus) => status === "approved";
  const canResume = (status: LeaveStatus) => status === "approved";

  return (
    <Container size="xl">
      <PageHeader title="My Leave Requests" subtitle="View and manage your leave requests" />
      <Card padding="lg">
        <Group gap="md" mb="md" wrap="wrap">
          <Select
            placeholder="Filter by status"
            value={filters.status}
            onChange={(v) => setFilters((p) => ({ ...p, status: v ?? "" }))}
            data={[
              { value: "", label: "All Statuses" },
              { value: "draft", label: "Draft" },
              { value: "submitted", label: "Submitted" },
              { value: "substitute_pending", label: "Substitute Pending" },
              { value: "unit_head_review", label: "Unit Head Review" },
              { value: "establishment_review", label: "Establishment Review" },
              { value: "final_sanction", label: "Final Sanction" },
              { value: "approved", label: "Approved" },
              { value: "rejected", label: "Rejected" },
              { value: "withdrawn", label: "Withdrawn" },
              { value: "cancelled", label: "Cancelled" },
              { value: "extension_requested", label: "Extension Requested" },
              { value: "resumption_pending", label: "Resumption Pending" },
              { value: "resumed", label: "Resumed" },
            ]}
            style={{ minWidth: 200 }}
          />
        </Group>
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
              render: (r) => (
                <Group>
                  {canWithdraw(r.status) && (
                    <Button variant="subtle" color="red" size="sm" onClick={() => handleWithdraw(r.id)}>
                      Withdraw
                    </Button>
                  )}
                  {canCancel(r.status) && (
                    <Button variant="subtle" color="red" size="sm" onClick={() => handleCancel(r.id)}>
                      Cancel
                    </Button>
                  )}
                  {canExtend(r.status) && r.category !== "CL" && r.category !== "RH" && r.category !== "SCL" && (
                    <Button variant="subtle" color="blue" size="sm" onClick={() => handleExtend(r.id)}>
                      Extend
                    </Button>
                  )}
                  {canResume(r.status) && r.category !== "CL" && r.category !== "RH" && r.category !== "SCL" && (
                    <Button variant="subtle" color="green" size="sm" onClick={() => handleResume(r.id)}>
                      Resume
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
          empty={{ title: "No leave requests", description: "You haven't applied for any leave yet." }}
        />
      </Card>
    </Container>
  );
}