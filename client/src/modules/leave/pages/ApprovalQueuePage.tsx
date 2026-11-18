import { Badge, Button, Card, Container, Group, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaStamp } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDecision, useQueue } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

const UNIT_HEAD_FINAL = ["CL", "RH"];

/** EL-UC-003 for the Unit Head, EL-UC-004/005 for the Sanctioning Authority.
 *  Both inboxes are the same table; only the actions differ, because CL/RH end
 *  at the Unit Head while everything else is recommended and routed on. */
export default function ApprovalQueuePage({ kind }: {
  kind: "requests" | "sanctions";
}) {
  const { data, isPending, error } = useQueue(kind);
  const decide = useDecision(kind);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function act(id: number, action: string) {
    decide.mutate({ id, action }, {
      onSuccess: () => notifications.show({
        color: "green", title: "Recorded",
        message: `Request #${id}: ${action.replace(/_/g, " ")}.`,
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not record", message: errorMessage(e),
      }),
    });
  }

  function actionsFor(row: LeaveApplication): [string, string][] {
    if (kind === "sanctions") {
      return [["approve", "Approve"], ["forward", "Forward"],
              ["reject", "Reject"]];
    }
    return UNIT_HEAD_FINAL.includes(row.leave_type)
      ? [["approve", "Approve"], ["reject", "Reject"]]
      : [["recommend", "Recommend"], ["not_recommend", "Not recommended"]];
  }

  return (
    <Container size="xl">
      <PageHeader
        title={kind === "requests" ? "Leave Requests" : "Sanction Queue"}
        subtitle={kind === "requests"
          ? "Decide CL and RH; recommend the rest for the sanctioning authority"
          : "Final sanctioning decisions on routed requests"}
      />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={1000}
          columns={[
            { key: "applicant", header: "Applicant",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>Employee #{r.user_id}</Text>
                  <Text size="xs" c="dimmed">{r.reason || "No reason given"}</Text>
                </Stack>
              ) },
            { key: "leave_type", header: "Category",
              render: (r) => (
                <Group gap={6}>
                  <Badge variant="light">{r.leave_type}</Badge>
                  {r.station_leave && (
                    <Badge variant="light" color="orange">Station</Badge>
                  )}
                </Group>
              ) },
            { key: "period", header: "Period",
              render: (r) => `${r.start_date} → ${r.end_date} (${r.days}d)` },
            { key: "recommendation", header: "Unit Head",
              render: (r) => r.unit_head_recommendation || "—" },
            { key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {actionsFor(r).map(([action, label]) => (
                    <Button
                      key={action} size="xs"
                      variant={action === "approve" ? "filled" : "subtle"}
                      color={action.includes("reject") || action === "not_recommend"
                        ? "red" : undefined}
                      loading={decide.isPending}
                      onClick={() => act(r.id, action)}
                    >
                      {label}
                    </Button>
                  ))}
                </Group>
              ) },
          ]}
          empty={{
            icon: FaStamp,
            title: "Nothing is waiting on you",
            description: "Requests routed to you will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
