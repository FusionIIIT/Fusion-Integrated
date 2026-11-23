import { useState } from "react";
import {
  Badge, Button, Card, Container, Select, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { FaPlus, FaShieldAlt } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAccess, useClubs, useConfirmClub, useCreateClub } from "../api/hooks";
import type { Club, ClubCategory } from "../api/types";
import { person, titleCase } from "../components/format";
import { LoadMore } from "../components/LoadMore";
import { PageError } from "../components/PageError";
import { PersonPicker } from "../components/PersonPicker";
import { done } from "../components/toasts";

const CATEGORIES: ClubCategory[] = ["technical", "sports", "cultural"];

export default function ClubAdminPage() {
  const access = useAccess();
  const clubs = useClubs();
  const [creating, setCreating] = useState(false);
  const [reviewing, setReviewing] = useState<Club | null>(null);
  const error = clubs.error ?? access.error;
  if (error) return <PageError error={error} />;
  const mayApprove = access.can("gymkhana.club.approve");

  return (
    <Container size="xl">
      <PageHeader
        title="Club Administration" subtitle="Establish clubs and confirm open ones"
        action={access.can("gymkhana.club.create") && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
            Create club
          </Button>
        )}
      />
      <Card padding="lg">
        <DataTable<Club>
          rows={clubs.rows} loading={clubs.loading || access.loading} rowKey={(c) => c.id}
          columns={[
            { key: "name", header: "Club", render: (c) => <Text fw={600}>{c.name}</Text> },
            { key: "category", header: "Category", render: (c) => titleCase(c.category) },
            {
              key: "status", header: "Status",
              render: (c) => (
                <Badge variant="light" color={c.status === "confirmed" ? "green" : "yellow"}>
                  {c.status}
                </Badge>
              ),
            },
            {
              key: "action", header: "", align: "right",
              render: (c) => c.status === "open" && mayApprove && (
                <Button size="xs" aria-label={`Review ${c.name}`} onClick={() => setReviewing(c)}>
                  Review
                </Button>
              ),
            },
          ]}
          empty={{
            icon: FaShieldAlt, title: "No clubs yet",
            description: "Create a club to start its approval.",
          }}
        />
        <LoadMore list={clubs} />
      </Card>
      {creating && <CreateClubModal onClose={() => setCreating(false)} />}
      {reviewing && <ReviewModal club={reviewing} onClose={() => setReviewing(null)} />}
    </Container>
  );
}

function ReviewModal({ club, onClose }: { club: Club; onClose: () => void }) {
  const confirm = useConfirmClub();
  return (
    <FormModal
      opened onClose={onClose} title={`Review ${club.name}`}
      subtitle="Approving confirms the club" submitLabel="Approve club"
      submitting={confirm.isPending} error={confirm.error}
      onSubmit={() => confirm.mutate(club.id, {
        onSuccess: () => {
          done("Club approved", `${club.name} is now confirmed.`);
          onClose();
        },
      })}
    >
      <Stack gap="xs">
        <Text size="sm"><b>Category:</b> {titleCase(club.category)}</Text>
        <Text size="sm"><b>Coordinator:</b> {person(club.coordinator_name, club.coordinator_id)}</Text>
        <Text size="sm">
          <b>Co-coordinator:</b> {person(club.co_coordinator_name, club.co_coordinator_id)}
        </Text>
        <Text size="sm">
          <b>Faculty Councillor:</b>{" "}
          {person(club.faculty_councillor_name, club.faculty_councillor_id)}
        </Text>
        <Text size="sm"><b>Description:</b> {club.description || "—"}</Text>
      </Stack>
    </FormModal>
  );
}

function CreateClubModal({ onClose }: { onClose: () => void }) {
  const create = useCreateClub();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [coordinator, setCoordinator] = useState<number | null>(null);
  const [coCoordinator, setCoCoordinator] = useState<number | null>(null);
  const [faculty, setFaculty] = useState<number | null>(null);

  const chosen = CATEGORIES.find((c) => c === category);
  function submit() {
    if (!chosen || coordinator === null || coCoordinator === null || faculty === null) return;
    create.mutate({
      name, description, category: chosen, coordinator_id: coordinator,
      co_coordinator_id: coCoordinator, faculty_councillor_id: faculty,
    }, {
      onSuccess: () => {
        done("Club created", `${name} is open and awaiting approval.`);
        onClose();
      },
    });
  }

  return (
    <FormModal
      opened onClose={onClose} title="Create club" subtitle="A new club is open until approved"
      submitLabel="Create" submitting={create.isPending} error={create.error} onSubmit={submit}
      disabled={!name.trim() || !chosen || coordinator === null || coCoordinator === null
        || faculty === null}
      disabledReason="Give a name, a category, both leaders and a Faculty Councillor."
    >
      <Stack gap="md">
        <TextInput label="Club name" required maxLength={120} value={name}
          onChange={(e) => setName(e.currentTarget.value)} />
        <Select label="Category" required value={category} onChange={setCategory}
          data={CATEGORIES.map((c) => ({ value: c, label: titleCase(c) }))} />
        <PersonPicker label="Coordinator" kind="student" value={coordinator}
          onChange={setCoordinator} />
        <PersonPicker label="Co-coordinator" kind="student" value={coCoordinator}
          onChange={setCoCoordinator} />
        <PersonPicker label="Faculty Councillor" kind="faculty" value={faculty}
          onChange={setFaculty} />
        <Textarea label="Description" autosize minRows={3} value={description}
          onChange={(e) => setDescription(e.currentTarget.value)} />
      </Stack>
    </FormModal>
  );
}
