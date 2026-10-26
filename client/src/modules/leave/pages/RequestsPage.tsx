import type { Column } from "../../../ui/components/DataTable";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { http, errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { NewLeaveRequest } from "../components/NewLeaveRequest";
import { useAuth } from "../../../auth/AuthProvider";
import { notifications } from "@mantine/notifications";
import { Button, Group, Badge } from "@mantine/core";

interface LeaveRequest {
  id: number;
  employee_id: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
  day_period: string;
  duration?: number | string;
  is_station_leave?: boolean;
  station_address?: string;
  station_contact?: string;
  substitute_id?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

interface CursorPage {
  results: LeaveRequest[];
  next: string | null;
  previous: string | null;
}

export default function RequestsPage() {
  const { data, error, isLoading } = useQuery<CursorPage>({
    queryKey: ["leave-requests"],
    queryFn: async () => {
      const res = await http.get("/leave/requests/");
      return res.data;
    },
  });

  const queryClient = useQueryClient();
  const auth = useAuth();

  const withdrawMutation = useMutation({
    mutationFn: async (id: number) => {
      return await http.post(`/leave/requests/${id}/withdraw/`);
    },
    onSuccess: () => {
      notifications.show({
        title: "Success",
        message: "Leave request withdrawn.",
        color: "green",
      });
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    },
    onError: (e: any) => {
      notifications.show({
        title: "Error",
        message: errorMessage(e),
        color: "red",
      });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async (id: number) => {
      return await http.post(`/leave/requests/${id}/cancel/`);
    },
    onSuccess: () => {
      notifications.show({
        title: "Success",
        message: "Approved leave cancelled and balance restored.",
        color: "green",
      });
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
      queryClient.invalidateQueries({ queryKey: ["leave-balances"] });
    },
    onError: (e: any) => {
      notifications.show({
        title: "Error",
        message: errorMessage(e),
        color: "red",
      });
    },
  });

  const approveMutation = useMutation({
    mutationFn: async (id: number) => {
      return await http.post(`/leave/requests/${id}/approve/`);
    },
    onSuccess: () => {
      notifications.show({
        title: "Success",
        message: "Leave request approved and balance deducted.",
        color: "green",
      });
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
      queryClient.invalidateQueries({ queryKey: ["leave-balances"] });
    },
    onError: (e: any) => {
      notifications.show({
        title: "Error",
        message: errorMessage(e),
        color: "red",
      });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async (id: number) => {
      return await http.post(`/leave/requests/${id}/reject/`, { reason: "Declined by sanctioning authority." });
    },
    onSuccess: () => {
      notifications.show({
        title: "Success",
        message: "Leave request rejected.",
        color: "orange",
      });
      queryClient.invalidateQueries({ queryKey: ["leave-requests"] });
    },
    onError: (e: any) => {
      notifications.show({
        title: "Error",
        message: errorMessage(e),
        color: "red",
      });
    },
  });

  const isCurrentOrFuture = (dateStr: string) => {
    if (!dateStr) return false;
    const today = new Date().toISOString().slice(0, 10);
    return dateStr >= today;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "approved":
        return "green";
      case "pending":
        return "blue";
      case "rejected":
        return "red";
      case "withdrawn":
        return "gray";
      case "cancelled":
        return "yellow";
      default:
        return "gray";
    }
  };

  const columns: Column<LeaveRequest>[] = [
    { key: "id", header: "ID" },
    { key: "employee_id", header: "Employee ID" },
    { key: "leave_type", header: "Leave Type" },
    {
      key: "day_period",
      header: "Period",
      render: (row) => (row.day_period === "first_half" ? "1st Half" : row.day_period === "second_half" ? "2nd Half" : "Full"),
    },
    { key: "start_date", header: "Start Date" },
    { key: "end_date", header: "End Date" },
    {
      key: "status",
      header: "Status",
      render: (row) => (
        <Badge color={getStatusColor(row.status)} variant="light" size="sm">
          {row.status.toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "is_station_leave",
      header: "Station Leave",
      render: (row) => (row.is_station_leave ? <Badge color="indigo" size="xs">YES</Badge> : "No"),
    },
    { key: "reason", header: "Reason" },
    {
      key: "actions",
      header: "Actions",
      render: (row) => {
        const isOwner = auth.session?.user.username === row.employee_id;
        const canSanction = auth.can("leave_cell.requests.sanction");
        const canManage = auth.can("leave_cell.requests.manage");

        return (
          <Group gap="xs">
            {/* Owner withdraw button for own pending request */}
            {row.status === "pending" && canManage && isOwner && (
              <Button
                size="xs"
                color="red"
                variant="light"
                onClick={() => withdrawMutation.mutate(row.id)}
                disabled={withdrawMutation.isPending}
              >
                Withdraw
              </Button>
            )}

            {/* Owner cancel button for approved leave before start */}
            {row.status === "approved" && canManage && isOwner && isCurrentOrFuture(row.start_date) && (
              <Button
                size="xs"
                color="orange"
                variant="light"
                onClick={() => cancelMutation.mutate(row.id)}
                disabled={cancelMutation.isPending}
              >
                Cancel
              </Button>
            )}

            {/* Sanctioning actions for reviewers on pending requests */}
            {row.status === "pending" && canSanction && (
              <>
                <Button
                  size="xs"
                  color="green"
                  variant="filled"
                  onClick={() => approveMutation.mutate(row.id)}
                  disabled={approveMutation.isPending}
                >
                  Approve
                </Button>
                <Button
                  size="xs"
                  color="red"
                  variant="outline"
                  onClick={() => rejectMutation.mutate(row.id)}
                  disabled={rejectMutation.isPending}
                >
                  Reject
                </Button>
              </>
            )}
          </Group>
        );
      },
    },
  ];

  const rows = data?.results ?? [];

  return (
    <>
      <PageHeader
        title="Leave Requests"
        subtitle="Manage employee leave applications, sanctioning decisions, and cancellations."
        action={<NewLeaveRequest />}
      />
      {error && <ErrorState error={error} />}
      <DataTable
        rows={rows}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No requests found",
          description: "No leave requests currently available.",
        }}
      />
    </>
  );
}
