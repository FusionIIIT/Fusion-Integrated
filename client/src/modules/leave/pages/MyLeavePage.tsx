import {
  Button, Card, Container, Group, SimpleGrid, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useBalances, useMyLeave, useRequestCancellation, useWithdraw,
} from "../api/hooks";
import type { LeaveApplication } from "../api/types";

/** EL-UC-012: balances and history in one place. */
export default function MyLeavePage() {
  const { data, isPending, error } = useMyLeave();
  const { data: balances } = useBalances();
  const withdraw = useWithdraw();
  const cancel = useRequestCancellation();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function act(mutation: typeof withdraw, id: number, label: string) {
    mutation.mutate({ id }, {
      onSuccess: () => notifications.show({
        color: "gray", title: label, message: `Request #${id}: ${label}.`,
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not continue", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="My Leave"
        subtitle="Your balances, and every request with the decision recorded against it"
      />
      <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }} mb="lg">
        {(balances ?? []).map((b) => (
          <Card key={b.id} padding="sm" withBorder>
            <Text size="xs" c="dimmed">{b.leave_type}</Text>
            <Text fw={700} size="xl">{b.available}</Text>
            <Text size="xs" c="dimmed">of {b.entitled} entitled</Text>
          </Card>
        ))}
      </SimpleGrid>
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            { key: "leave_type", header: "Category",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.leave_type}{r.kind !== "leave"
                    ? ` (${r.kind})` : ""}</Text>
                  <Text size="xs" c="dimmed">{r.days} day(s)</Text>
                </Stack>
              ) },
            { key: "period", header: "Period",
              render: (r) => `${r.start_date} → ${r.end_date}` },
            { key: "pending_role", header: "With",
              render: (r) => r.pending_role || "—" },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            { key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {r.status.startsWith("pending_") && (
                    <Button
                      size="xs" variant="subtle" color="gray"
                      loading={withdraw.isPending}
                      onClick={() => act(withdraw, r.id, "Withdrawn")}
                    >
                      Withdraw
                    </Button>
                  )}
                  {r.status === "approved" && r.kind === "leave" && (
                    <Button
                      size="xs" variant="subtle" color="red"
                      loading={cancel.isPending}
                      onClick={() => act(cancel, r.id, "Cancellation requested")}
                    >
                      Request cancellation
                    </Button>
                  )}
                </Group>
              ) },
          ]}
          empty={{
            icon: FaCalendarCheck,
            title: "You have no leave requests yet",
            description: "Anything you apply for will be tracked here.",
          }}
        />
      </Card>
    </Container>
  );
}
