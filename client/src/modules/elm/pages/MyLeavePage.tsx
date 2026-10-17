import { Button, Card, Container } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLeaveTransition, useMyLeave } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { leaveColumns } from "./columns";

export default function MyLeavePage() {
  const { data, isPending, error } = useMyLeave();
  const transition = useLeaveTransition();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function withdraw(r: LeaveRequest) {
    transition.mutate({ id: r.id, to_status: "withdrawn" }, {
      onSuccess: () => notifications.show({
        color: "gray", title: "Withdrawn", message: "Your request has been withdrawn.",
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not withdraw", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="A pending request cannot be edited; withdraw it and apply again"
      />
      <Card padding="lg">
        <DataTable<LeaveRequest>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          columns={[
            ...leaveColumns,
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => r.allowed_transitions.includes("withdrawn") ? (
                <Button size="xs" variant="subtle" color="gray"
                        loading={transition.isPending} onClick={() => withdraw(r)}>
                  Withdraw
                </Button>
              ) : null,
            },
          ]}
          empty={{
            icon: FaCalendarAlt,
            title: "No leave requests yet",
            description: "Requests you submit will be tracked here.",
          }}
        />
      </Card>
    </Container>
  );
}
