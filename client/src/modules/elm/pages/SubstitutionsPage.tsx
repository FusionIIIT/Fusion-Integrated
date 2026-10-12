import { Button, Card, Container } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRespondSubstitution, useSubstitutions } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { LeaveTable } from "../components/LeaveTable";
import { NoteModal } from "../components/NoteModal";

export default function SubstitutionsPage() {
  const { data, isPending, error } = useSubstitutions();
  const respond = useRespondSubstitution();
  const [pick, setPick] = useState<{ row: LeaveRequest; accept: boolean } | null>(null);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Substitution Requests"
        subtitle="Colleagues who nominated you to cover their responsibilities" />
      <Card withBorder padding="md">
        <LeaveTable rows={data?.results ?? []} loading={isPending} showApplicant
          empty={{ title: "No substitution requests" }}
          actions={(r) => r.status === "awaiting_substitute" ? [
            <Button key="a" size="xs" onClick={() => setPick({ row: r, accept: true })}>
              Accept</Button>,
            <Button key="d" size="xs" variant="light" color="red"
              onClick={() => setPick({ row: r, accept: false })}>Decline</Button>,
          ] : null} />
      </Card>
      <NoteModal
        opened={pick != null}
        title={pick?.accept ? "Accept this responsibility?" : "Decline this nomination?"}
        subtitle={pick ? `${pick.row.start_date} to ${pick.row.end_date}: ${pick.row.responsibility}` : ""}
        label="Note (optional)" submitLabel={pick?.accept ? "Accept" : "Decline"}
        danger={!pick?.accept} submitting={respond.isPending} onClose={() => setPick(null)}
        onSubmit={(note) => pick && respond.mutate({ id: pick.row.id, accept: pick.accept, note }, {
          onSuccess: () => setPick(null),
          onError: (e) => notifications.show({ color: "red", title: "Not recorded",
            message: errorMessage(e) }),
        })}
      />
    </Container>
  );
}
