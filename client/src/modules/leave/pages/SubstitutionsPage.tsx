import { Button, Card, Container, Group, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { FaUserCheck } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useRespond, useSubstitutions } from "../api/hooks";
import type { SubstitutionRequest } from "../api/types";
import { period } from "../components/fields";

/** EL-UC-002: accept or decline covering for a colleague; a decline needs a reason. */
export default function SubstitutionsPage() {
  const { data, isPending, error } = useSubstitutions();
  const respond = useRespond();
  const [declining, setDeclining] = useState<SubstitutionRequest | null>(null);
  const [remarks, setRemarks] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function answer(s: SubstitutionRequest, accept: boolean) {
    respond.mutate({ id: s.id, accept, remarks }, {
      onSuccess: () => {
        notifications.show({ color: accept ? "green" : "gray",
          title: accept ? "Accepted" : "Declined", message: `${s.applicant_name} has been told.` });
        setDeclining(null);
        setRemarks("");
      },
      onError: (e) => {
        if (accept) notifications.show({ color: "red", title: "Not recorded", message: errorMessage(e) });
      },
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Substitute Requests"
        subtitle="Colleagues who have asked you to cover their responsibilities while away" />
      <Card padding="lg">
        <DataTable<SubstitutionRequest>
          rows={data ?? []} loading={isPending} rowKey={(r) => r.id}
          columns={[
            { key: "who", header: "Colleague", render: (r) => <Text fw={600}>{r.applicant_name}</Text> },
            { key: "leave", header: "Leave", render: (r) => r.request.category_label },
            { key: "period", header: "Responsibility period", render: (r) => period(r.request) },
            { key: "actions", header: "", align: "right", render: (r) => (
              <Group gap="xs" justify="flex-end">
                <Button size="xs" loading={respond.isPending} onClick={() => answer(r, true)}>Accept</Button>
                <Button size="xs" variant="light" color="gray" onClick={() => setDeclining(r)}>Decline</Button>
              </Group>) },
          ]}
          empty={{ icon: FaUserCheck, title: "Nobody is waiting for your answer",
            description: "When a colleague nominates you as their substitute it appears here." }}
        />
      </Card>
      <FormModal opened={declining != null} onClose={() => setDeclining(null)}
        title="Decline to cover" subtitle={declining?.applicant_name} danger submitLabel="Decline"
        submitting={respond.isPending} error={respond.error}
        disabled={!remarks.trim()} disabledReason="Tell your colleague why."
        onSubmit={() => declining && answer(declining, false)}>
        <Textarea label="Reason" required value={remarks} autosize minRows={2}
          onChange={(e) => setRemarks(e.currentTarget.value)} />
      </FormModal>
    </Container>
  );
}
