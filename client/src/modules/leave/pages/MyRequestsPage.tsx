import { useState } from "react";
import {
  Badge, Button, Container, Group, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaClipboardList } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import {
  useMyRequests, useRequestCounts, useSubmitRequest, useWithdrawRequest,
} from "../api/hooks";
import { isPending, type LeaveRequest } from "../api/types";

/** EL-UC-001/002: my own requests, and what I can still do to each. */
export default function MyRequestsPage() {
  const rows = useMyRequests();
  const counts = useRequestCounts();
  const withdraw = useWithdrawRequest();
  const submit = useSubmitRequest();

  if (rows.isError) {
    return <Container size="xl"><ErrorState error={rows.error} /></Container>;
  }

  const items = rows.data ?? [];

  const columns: Column<LeaveRequest>[] = [
    {
      key: "category",
      header: "Type",
      render: (r) => (
        <Stack gap={2}>
          <Text size="sm" fw={600}>{r.category_label}</Text>
          <Text size="xs" c="dimmed">{r.requested_days} day(s)</Text>
        </Stack>
      ),
    },
    {
      key: "period",
      header: "Period",
      render: (r) => (
        <Text size="sm">
          {r.start_date} → {r.end_date}
          {r.half_day && ` (${r.half})`}
        </Text>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <StatusBadge status={r.status} />,
    },
    {
      key: "recommendation",
      header: "Unit Head",
      render: (r) => (r.unit_head_recommendation
        ? <Badge color={r.unit_head_recommendation === "recommended"
          ? "green" : "orange"} variant="light" size="sm">
          {r.unit_head_recommendation.replace(/_/g, " ")}
        </Badge>
        : <Text size="xs" c="dimmed">—</Text>),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (r) => {
        const actions: { label: string; run: () => void; danger?: boolean }[] = [];
        if (r.status === "draft") {
          actions.push({
            label: "Submit",
            run: () => submit.mutate({ id: r.id }),
          });
        }
        if (isPending(r.status)) {
          actions.push({
            label: "Withdraw",
            danger: true,
            run: () => withdraw.mutate(r.id, {
              onSuccess: () => notifications.show({
                color: "gray", title: "Withdrawn",
                message: "Your request has been withdrawn.",
              }),
              onError: (e) => notifications.show({
                color: "red", title: "Could not withdraw",
                message: String((e as { response?: { data?: { error?: {
                  message?: string } } } })?.response?.data?.error
                  ?.message ?? "Please try again."),
              }),
            }),
          });
        }
        if (!actions.length) {
          return <Text size="xs" c="dimmed">—</Text>;
        }
        return (
          <Group gap="xs" justify="flex-end" wrap="nowrap">
            {actions.map((a) => (
              <Button key={a.label} size="compact-xs" variant="subtle"
                      color={a.danger ? "red" : undefined} onClick={a.run}>
                {a.label}
              </Button>
            ))}
          </Group>
        );
      },
    },
  ];

  const summary = Object.entries(counts.data ?? {})
    .filter(([, n]) => n > 0)
    .map(([state, n]) => `${state.replace(/_/g, " ")}: ${n}`);

  return (
    <Container size="xl">
      <PageHeader title="My Requests" subtitle={summary.join("  ·  ")} />
      <DataTable
        rows={items}
        columns={columns}
        loading={rows.isPending}
        rowKey={(r) => r.id}
        minWidth={860}
        empty={{
          icon: FaClipboardList,
          title: "No leave requests yet",
          description: "Apply for leave and it will appear here.",
        }}
      />
    </Container>
  );
}