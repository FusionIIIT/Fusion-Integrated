import {
  Alert, Button, Container, Group, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUserRoundCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useRespondToNomination, useSubstitutions } from "../api/hooks";
import type { SubstituteNomination } from "../api/types";

/** EL-UC-003/004: nominations addressed to me.
 *
 *  Only a pending one is answerable; a declined nomination returns the
 *  application to the applicant, who nominates someone else (BR-EL-014). */
export default function SubstitutionsPage() {
  const queue = useSubstitutions();
  const respond = useRespondToNomination();

  if (queue.isError) {
    return <Container size="lg"><ErrorState error={queue.error} /></Container>;
  }

  const rows = queue.data ?? [];
  const pending = rows.filter((r) => r.status === "pending");

  function answer(id: number, accept: boolean) {
    respond.mutate({ id, accept }, {
      onSuccess: () => notifications.show({
        color: accept ? "green" : "orange",
        title: accept ? "Accepted" : "Declined",
        message: accept
          ? "The applicant has been told you will cover."
          : "The applicant has been asked to nominate someone else.",
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not record your answer",
        message: errorMessage(e),
      }),
    });
  }

  const columns: Column<SubstituteNomination>[] = [
    { key: "request", header: "Request",
      render: (r) => <Text size="sm">#{r.leave_request}</Text> },
    { key: "period", header: "Cover period",
      render: (r) => <Text size="sm">{r.period_start} → {r.period_end}</Text> },
    { key: "status", header: "Status",
      render: (r) => <StatusBadge status={r.status} /> },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (r) => (r.status === "pending" ? (
        <Group gap="xs" justify="flex-end" wrap="nowrap">
          <Button size="compact-xs" onClick={() => answer(r.id, true)}>
            Accept
          </Button>
          <Button size="compact-xs" variant="light" color="orange"
                  onClick={() => answer(r.id, false)}>
            Decline
          </Button>
        </Group>
      ) : <Text size="xs" c="dimmed">—</Text>),
    },
  ];

  return (
    <Container size="lg">
      <PageHeader
        title="Substitute Requests"
        subtitle={`${pending.length} awaiting your answer`}
      />
      {!!pending.length && (
        <Alert color="blue" variant="light" mb="md">
          Declining sends the application back to the applicant to nominate
          someone else. It does not go to the Unit Head.
        </Alert>
      )}
      <Stack gap={4}>
        <DataTable
          rows={rows}
          columns={columns}
          loading={queue.isPending}
          rowKey={(r) => r.id}
          minWidth={620}
          empty={{
            icon: FaUserRoundCheck,
            title: "No nominations for you",
            description: "You will be asked here when somebody nominates you.",
          }}
        />
      </Stack>
    </Container>
  );
}