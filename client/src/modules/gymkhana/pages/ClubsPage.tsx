import { useState } from "react";
import { Button, Card, Container, Text, Textarea } from "@mantine/core";
import { FaUsers } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApply, useClubs } from "../api/hooks";
import type { Club } from "../api/types";
import { ClubStatus } from "../components/ClubStatus";
import { notifyDone } from "../components/notify";

const CATEGORY: Record<string, string> = {
  technical: "Technical", sports: "Sports", cultural: "Cultural" };

/** UC-GYM-004: confirmed clubs, and an application to any not yet applied to. */
export default function ClubsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useClubs({ status: "confirmed" });
  const apply = useApply();
  const [club, setClub] = useState<Club | null>(null);
  const [description, setDescription] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function close() {
    setClub(null);
    setDescription("");
    apply.reset();
  }

  function submit() {
    if (!club) return;
    apply.mutate({ club_id: club.id, description }, {
      onSuccess: () => {
        notifyDone("Application sent", `Your application to ${club.name} is open.`);
        close();
      },
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Clubs" subtitle="Confirmed Gymkhana clubs you can apply to join" />
      <Card padding="lg">
        <DataTable<Club>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(c) => c.id}
          empty={{ icon: FaUsers, title: "No clubs yet",
            description: "Clubs appear here once Student Admin confirms them." }}
          columns={[
            { key: "name", header: "Club", render: (c) => (
              <div><Text fw={600}>{c.name}</Text>
                <Text size="xs" c="dimmed" lineClamp={2}>{c.description}</Text></div>) },
            { key: "category", header: "Category", render: (c) => CATEGORY[c.category] },
            { key: "mine", header: "Your application", render: (c) =>
              c.my_membership ? <ClubStatus status={c.my_membership} />
                : <Text size="sm" c="dimmed">None</Text> },
            { key: "action", header: "", align: "right", render: (c) =>
              !c.my_membership && can("gymkhana.membership.create") ? (
                <Button size="xs" onClick={() => setClub(c)}
                  aria-label={`Apply to ${c.name}`}>Apply</Button>) : null },
          ]}
        />
      </Card>
      <FormModal
        opened={club !== null} onClose={close} onSubmit={submit}
        title={`Apply to ${club?.name ?? ""}`} submitLabel="Send application"
        submitting={apply.isPending} error={apply.error}
        disabled={!description.trim()} disabledReason="Describe why you want to join."
      >
        <Textarea label="Why you want to join, or your achievements" required autosize
          minRows={4} maxLength={4000} value={description}
          onChange={(e) => setDescription(e.currentTarget.value)} />
      </FormModal>
    </Container>
  );
}
