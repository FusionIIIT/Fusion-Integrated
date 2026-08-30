import { useState } from "react";
import { Button, Card, Container, Group, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUserFriends } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DecisionModal } from "../components/DecisionModal";
import { PeriodCell } from "../components/PeriodCell";
import { useNominations, useRespondToNomination } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function SubstitutePage() {
  const { data, isPending, error } = useNominations();
  const respond = useRespondToNomination();
  const [deciding, setDeciding] = useState<
    { request: LeaveRequest; accepted: boolean } | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function confirm(remark: string) {
    if (!deciding) return;
    const { request, accepted } = deciding;
    respond.mutateAsync({ id: request.id, accepted, remark })
      .then(() => {
        setDeciding(null);
        notifications.show({
          color: accepted ? "green" : "gray",
          title: accepted ? "Accepted" : "Declined",
          message: accepted
            ? "The request has moved on to the unit head."
            : "The applicant has been asked to nominate someone else.",
        });
      })
      .catch((e) => notifications.show({
        color: "red", title: "Not recorded", message: errorMessage(e),
      }));
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Standing In"
        subtitle="Colleagues who have nominated you to hold their responsibilities"
      />
      <Card padding="lg">
        <Text size="sm" c="dimmed" mb="md">
          Accepting means you will carry their duties for the period shown.
          Nothing moves forward until you answer.
        </Text>
        <DataTable<LeaveRequest>
          rows={data ?? []} loading={isPending} rowKey={(r) => r.id} minWidth={860}
          columns={[
            { key: "user", header: "Applicant", render: (r) => r.user_id },
            { key: "category", header: "Type", render: (r) => r.category },
            { key: "period", header: "Period",
              render: (r) => <PeriodCell request={r} /> },
            { key: "reason", header: "Reason", render: (r) => r.reason },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  <Button
                    size="xs" variant="subtle" color="red"
                    onClick={() => setDeciding({ request: r, accepted: false })}
                  >
                    Decline
                  </Button>
                  <Button
                    size="xs"
                    onClick={() => setDeciding({ request: r, accepted: true })}
                  >
                    Accept
                  </Button>
                </Group>
              ),
            },
          ]}
          empty={{
            icon: FaUserFriends,
            title: "Nobody has nominated you",
            description: "Nominations waiting on your answer appear here.",
          }}
        />
      </Card>

      <DecisionModal
        request={deciding?.request ?? null}
        approve={deciding?.accepted ?? true}
        verb="Accept"
        submitting={respond.isPending}
        onClose={() => setDeciding(null)}
        onConfirm={confirm}
      />
    </Container>
  );
}
