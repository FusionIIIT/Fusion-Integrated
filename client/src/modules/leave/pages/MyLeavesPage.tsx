import { useState } from "react";
import { Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useCancelLeave, useLeaveRequests, useWithdrawLeave } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function MyLeavesPage() {
  const { data, isPending, error } = useLeaveRequests();
  const cancel = useCancelLeave();
  const withdraw = useWithdrawLeave();
  const [acting, setActing] = useState<number | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function doCancel(r: LeaveRequest) {
    setActing(r.id);
    cancel.mutate(r.id, {
      onSuccess: () => notifications.show({ color: "gray", title: "Cancelled", message: "Leave cancelled." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not cancel", message: errorMessage(e) }),
      onSettled: () => setActing(null),
    });
  }

  function doWithdraw(r: LeaveRequest) {
    setActing(r.id);
    withdraw.mutate(r.id, {
      onSuccess: () => notifications.show({ color: "gray", title: "Withdrawn", message: "Leave withdrawn." }),
      onError: (e) => notifications.show({ color: "red", title: "Could not withdraw", message: errorMessage(e) }),
      onSettled: () => setActing(null),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="My Leaves" subtitle="Your leave applications and their status." />
      <Card padding="lg">
        <DataTable<LeaveRequest>
          rows={(data ?? []) as LeaveRequest[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            { key: "leave_type_code", header: "Type", render: (r) => r.leave_type_code },
            { key: "start_date", header: "Start", render: (r) => r.start_date },
            { key: "end_date", header: "End", render: (r) => r.end_date },
            { key: "duration_days", header: "Days", render: (r) => r.duration_days },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            { key: "reason", header: "Reason", render: (r) => r.reason },
          ]}
          empty={{ title: "No leave requests yet", description: "Apply for leave to see it here." }}
        />
        <Stack gap="xs" mt="md">
          {(data ?? []).map((r) => (
            r.status === "pending" ? (
              <Group key={r.id} justify="flex-end" gap="xs">
                <Text size="xs" c="dimmed">#{r.id}</Text>
                <Button size="xs" variant="subtle" color="gray" loading={acting === r.id} onClick={() => doWithdraw(r)}>Withdraw</Button>
                <Button size="xs" variant="subtle" color="red" loading={acting === r.id} onClick={() => doCancel(r)}>Cancel</Button>
              </Group>
            ) : null
          ))}
        </Stack>
      </Card>
    </Container>
  );
}