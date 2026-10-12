import { Button, Card, Container } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useResumptions, useVerify } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import { LeaveTable } from "../components/LeaveTable";
import { NoteModal } from "../components/NoteModal";

export default function ResumptionsPage() {
  const { data, isPending, error } = useResumptions();
  const verify = useVerify();
  const [pick, setPick] = useState<{ row: LeaveRequest; ok: boolean } | null>(null);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Resumptions"
        subtitle="Verify the actual return to duty; early returns restore unused leave" />
      <Card withBorder padding="md">
        <LeaveTable rows={data?.results ?? []} loading={isPending} showApplicant
          empty={{ title: "No resumptions to verify" }}
          actions={(r) => [
            <Button key="v" size="xs" onClick={() => setPick({ row: r, ok: true })}>
              Verify return on {r.actual_return_date}</Button>,
            <Button key="n" size="xs" variant="light" color="red"
              onClick={() => setPick({ row: r, ok: false })}>Cannot verify</Button>,
          ]} />
      </Card>
      <NoteModal
        opened={pick != null} title={pick?.ok ? "Verify return" : "Return cannot be verified"}
        label="Note" required={pick ? !pick.ok : false}
        submitLabel={pick?.ok ? "Verify" : "Send back"} danger={!pick?.ok}
        submitting={verify.isPending} onClose={() => setPick(null)}
        onSubmit={(note) => pick && verify.mutate({ id: pick.row.id, verified: pick.ok, note }, {
          onSuccess: () => setPick(null),
          onError: (e) => notifications.show({ color: "red", title: "Not recorded",
            message: errorMessage(e) }),
        })}
      />
    </Container>
  );
}
