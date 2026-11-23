import { useState } from "react";
import { Badge, Button, Card, Container, Stack, Text, Textarea } from "@mantine/core";
import { FaUsers } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAccess, useApply, useClubs, useMemberships } from "../api/hooks";
import type { Club } from "../api/types";
import { person, titleCase } from "../components/format";
import { LoadMore } from "../components/LoadMore";
import { PageError } from "../components/PageError";
import { done } from "../components/toasts";

export default function ClubsPage() {
  const access = useAccess();
  const clubs = useClubs();
  const mayApply = access.can("gymkhana.membership.create");
  const mine = useMemberships({}, mayApply);
  const [applyingTo, setApplyingTo] = useState<Club | null>(null);

  const error = clubs.error ?? access.error ?? mine.error;
  if (error) return <PageError error={error} />;
  const statusOf = new Map(mine.rows.map((m) => [m.club_id, m.status]));

  return (
    <Container size="xl">
      <PageHeader title="Gymkhana Clubs" subtitle="Student clubs and who leads them" />
      <Card padding="lg">
        <DataTable<Club>
          rows={clubs.rows}
          loading={clubs.loading || mine.loading || access.loading}
          rowKey={(c) => c.id}
          columns={[
            {
              key: "name", header: "Club",
              render: (c) => (
                <Stack gap={0}>
                  <Text fw={600}>{c.name}</Text>
                  <Text size="xs" c="dimmed">{c.description}</Text>
                </Stack>
              ),
            },
            { key: "category", header: "Category", render: (c) => titleCase(c.category) },
            {
              key: "leaders", header: "Coordinator and co-coordinator",
              render: (c) => (
                <Stack gap={0}>
                  <Text size="sm">{person(c.coordinator_name, c.coordinator_id)}</Text>
                  <Text size="sm">{person(c.co_coordinator_name, c.co_coordinator_id)}</Text>
                </Stack>
              ),
            },
            {
              key: "faculty", header: "Faculty Councillor",
              render: (c) => person(c.faculty_councillor_name, c.faculty_councillor_id),
            },
            {
              key: "action", header: "", align: "right",
              render: (c) => {
                const status = statusOf.get(c.id);
                if (status) {
                  return (
                    <Badge variant="light" color={status === "confirmed" ? "green" : "blue"}>
                      {status === "confirmed" ? "Member" : "Applied"}
                    </Badge>
                  );
                }
                if (c.status === "open") {
                  return <Badge variant="light" color="yellow">Awaiting approval</Badge>;
                }
                return mayApply ? (
                  <Button size="xs" aria-label={`Apply to ${c.name}`}
                    onClick={() => setApplyingTo(c)}>
                    Apply
                  </Button>
                ) : null;
              },
            },
          ]}
          empty={{
            icon: FaUsers, title: "No clubs yet",
            description: "Clubs appear here once Student Admin has approved them.",
          }}
        />
        <LoadMore list={clubs} />
      </Card>
      {applyingTo && <ApplyModal club={applyingTo} onClose={() => setApplyingTo(null)} />}
    </Container>
  );
}

function ApplyModal({ club, onClose }: { club: Club; onClose: () => void }) {
  const apply = useApply();
  const [description, setDescription] = useState("");
  return (
    <FormModal
      opened onClose={onClose} title={`Apply to ${club.name}`}
      subtitle="The club's coordinator or co-coordinator will review your application"
      submitLabel="Submit application" submitting={apply.isPending} error={apply.error}
      disabled={!description.trim()} disabledReason="Describe your interest or achievements."
      onSubmit={() => apply.mutate({ club_id: club.id, description }, {
        onSuccess: () => {
          done("Application submitted", `Your application to ${club.name} is open.`);
          onClose();
        },
      })}
    >
      <Textarea
        label="Achievements or application description" required autosize minRows={4}
        value={description} onChange={(e) => setDescription(e.currentTarget.value)}
      />
    </FormModal>
  );
}
