import { Button, Card, Container, Group, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUserFriends } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useNominationResponse, useNominations } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

/** EL-UC-002. Consent is a gate: routing waits here until this is answered. */
export default function SubstituteRequestsPage() {
  const { data, isPending, error } = useNominations();
  const respond = useNominationResponse();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function answer(id: number, accept: boolean) {
    respond.mutate({ id, accept }, {
      onSuccess: () => notifications.show({
        color: accept ? "green" : "gray",
        title: accept ? "Accepted" : "Declined",
        message: `You ${accept ? "accepted" : "declined"} request #${id}.`,
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not respond", message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Substitute Requests"
        subtitle="Responsibility you have been nominated to carry during a colleague's absence"
      />
      <Card padding="lg">
        <DataTable<LeaveApplication>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "applicant", header: "Applicant",
              render: (r) => <Text>Employee #{r.user_id}</Text> },
            { key: "leave_type", header: "Category", render: (r) => r.leave_type },
            { key: "period", header: "Responsibility period",
              render: (r) => `${r.start_date} → ${r.end_date}` },
            { key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  <Button
                    size="xs" loading={respond.isPending}
                    onClick={() => answer(r.id, true)}
                  >
                    Accept
                  </Button>
                  <Button
                    size="xs" variant="subtle" color="red"
                    loading={respond.isPending}
                    onClick={() => answer(r.id, false)}
                  >
                    Decline
                  </Button>
                </Group>
              ) },
          ]}
          empty={{
            icon: FaUserFriends,
            title: "No substitute requests",
            description: "Nominations needing your consent will appear here.",
          }}
        />
      </Card>
    </Container>
  );
}
