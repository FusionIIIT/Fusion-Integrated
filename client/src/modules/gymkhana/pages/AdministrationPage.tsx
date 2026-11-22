import { useState } from "react";
import { Button, Card, Container, Select, Text, Textarea, TextInput } from "@mantine/core";
import { FaPlus, FaUsers } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApproveClub, useClubs, useCreateClub } from "../api/hooks";
import type { Club } from "../api/types";
import { ClubStatus } from "../components/ClubStatus";
import { notifyDone, notifyFailed } from "../components/notify";
import { PersonPicker } from "../components/PersonPicker";

// A name when the directory knows the person; otherwise their id, marked as such.
function personLabel(name: string | undefined, id: number | undefined): string {
  if (name) return name;
  return id === undefined ? "Not assigned" : `User ${id} (not in the directory)`;
}

const CATEGORIES = [{ value: "technical", label: "Technical" },
  { value: "sports", label: "Sports" }, { value: "cultural", label: "Cultural" }];

/** UC-GYM-001 and UC-GYM-011, for Student Admin. */
export default function AdministrationPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useClubs();
  const approve = useApproveClub();
  const [creating, setCreating] = useState(false);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  function confirm(c: Club) {
    approve.mutate(c.id, {
      onSuccess: () => notifyDone("Club confirmed", `${c.name} is now confirmed.`),
      onError: (e) => notifyFailed("Could not confirm", e),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Club Administration" subtitle="Create clubs and confirm open ones"
        action={can("gymkhana.club.create") ? (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
            Create club</Button>) : null} />
      <Card padding="lg">
        <DataTable<Club>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(c) => c.id}
          empty={{ icon: FaUsers, title: "No clubs yet",
            description: "Create the first club; it stays open until you confirm it." }}
          columns={[
            { key: "name", header: "Club", render: (c) => <Text fw={600}>{c.name}</Text> },
            { key: "category", header: "Category", render: (c) => c.category },
            { key: "leaders", header: "Coordinator / co-coordinator", render: (c) => (
              <div><Text size="sm">{personLabel(c.leader_names.coordinator,
                c.leaders.coordinator)}</Text>
              <Text size="sm">{personLabel(c.leader_names.co_coordinator,
                c.leaders.co_coordinator)}</Text></div>) },
            { key: "councillor", header: "Faculty councillor",
              render: (c) => personLabel(c.councillor_name, c.faculty_councillor_user_id) },
            { key: "status", header: "Status", render: (c) => <ClubStatus status={c.status} /> },
            { key: "action", header: "", align: "right", render: (c) =>
              c.status === "open" && can("gymkhana.club.approve") ? (
                <Button size="xs" onClick={() => confirm(c)} loading={approve.isPending}
                  aria-label={`Confirm ${c.name}`}>Confirm</Button>) : null },
          ]}
        />
      </Card>
      <CreateClubModal opened={creating} onClose={() => setCreating(false)} />
    </Container>
  );
}

function CreateClubModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const create = useCreateClub();
  const [name, setName] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [coord, setCoord] = useState<number | null>(null);
  const [co, setCo] = useState<number | null>(null);
  const [councillor, setCouncillor] = useState<number | null>(null);
  const missing = !name.trim() || !category || !description.trim() || coord === null
    || co === null || councillor === null;

  function close() {
    setName(""); setCategory(null); setDescription("");
    setCoord(null); setCo(null); setCouncillor(null);
    create.reset();
    onClose();
  }

  function submit() {
    if (missing) return;
    create.mutate({ name, category: category ?? "", description, coordinator_user_id: coord,
      co_coordinator_user_id: co, faculty_councillor_user_id: councillor }, {
      onSuccess: (c) => { notifyDone("Club created", `${c.name} is open until confirmed.`);
        close(); },
    });
  }

  return (
    <FormModal opened={opened} onClose={close} onSubmit={submit} title="Create a club"
      subtitle="Coordinators must be students; the councillor must be faculty"
      submitLabel="Create club" submitting={create.isPending} error={create.error}
      disabled={missing} disabledReason="Fill in every field.">
      <TextInput label="Name" required maxLength={120} value={name}
        onChange={(e) => setName(e.currentTarget.value)} />
      <Select mt="sm" label="Category" required data={CATEGORIES} value={category}
        onChange={setCategory} />
      <Textarea mt="sm" label="Description" required autosize minRows={3} maxLength={4000}
        value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
      <PersonPicker label="Coordinator" kind="student" value={coord} onChange={setCoord}
        required />
      <PersonPicker label="Co-coordinator" kind="student" value={co} onChange={setCo} required />
      <PersonPicker label="Club Faculty Councillor" kind="faculty" value={councillor}
        onChange={setCouncillor} required />
    </FormModal>
  );
}
