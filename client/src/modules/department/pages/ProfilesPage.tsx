import { Badge, Button, NumberInput, Select, Stack, Table, TextInput } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateProfile, useProfiles, useUpdateProfile } from "../api/hooks";
import type { ProfileInput } from "../api/types";
import { ActionError, PageBody, useDialog } from "../components/PageBody";
import { useCanAct } from "../components/acting";

const BLANK: ProfileInput = {
  kind: "faculty", user_id: null, display_name: "", office: "", research_interests: "",
  current_position: "", graduation_year: null,
};

export default function ProfilesPage() {
  const can = useCanAct();
  const { data, isPending, error } = useProfiles();
  const create = useCreateProfile();
  const update = useUpdateProfile();
  const { dialog: form, setDialog: setForm, opened } = useDialog<ProfileInput>();
  const rows = data?.results ?? [];
  const manage = can("department.profile.update");

  return (
    <PageBody
      isPending={isPending} error={error} isEmpty={rows.length === 0} emptyTitle="No department profiles yet"
      header={(
        <PageHeader
          title="People" subtitle="Faculty, students and alumni, shown at the detail your role may see"
          action={manage && <Button onClick={() => setForm(BLANK)}>Add profile</Button>}
        />
      )}
      overlays={(
        <FormModal
          opened={opened} onClose={() => setForm(null)} title="Add profile"
          onSubmit={() => form && create.mutate(form, { onSuccess: () => setForm(null) })}
          submitting={create.isPending} error={create.error}
        >
          {form && (
            <Stack>
              <Select label="Kind" allowDeselect={false} value={form.kind}
                data={[{ value: "faculty", label: "Faculty" }, { value: "student", label: "Student" },
                  { value: "alumni", label: "Alumni" }]}
                onChange={(v) => setForm({ ...form, kind: (v ?? "faculty") as ProfileInput["kind"] })} />
              {form.kind !== "alumni" && (
                <NumberInput label="User id" value={form.user_id ?? ""}
                  onChange={(v) => setForm({ ...form, user_id: typeof v === "number" ? v : null })} />
              )}
              <TextInput label="Name" value={form.display_name}
                onChange={(e) => setForm({ ...form, display_name: e.currentTarget.value })} />
              <TextInput label="Office" value={form.office} onChange={(e) => setForm({ ...form, office: e.currentTarget.value })} />
              <TextInput label="Research interests" value={form.research_interests}
                onChange={(e) => setForm({ ...form, research_interests: e.currentTarget.value })} />
              {form.kind === "alumni" && (
                <>
                  <NumberInput label="Graduation year" value={form.graduation_year ?? ""}
                    onChange={(v) => setForm({ ...form, graduation_year: typeof v === "number" ? v : null })} />
                  <TextInput label="Current position" value={form.current_position}
                    onChange={(e) => setForm({ ...form, current_position: e.currentTarget.value })} />
                </>
              )}
            </Stack>
          )}
        </FormModal>
      )}
    >
      <ActionError errors={[update.error]} />
      <Table striped withTableBorder>
        <Table.Thead>
          <Table.Tr><Table.Th>Name</Table.Th><Table.Th>Kind</Table.Th><Table.Th>Programme</Table.Th>
            <Table.Th>Contact</Table.Th><Table.Th>Office</Table.Th><Table.Th /></Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((p) => (
            <Table.Tr key={p.id} style={p.is_active === false ? { opacity: 0.6 } : undefined}>
              <Table.Td>{p.display_name}</Table.Td>
              <Table.Td><Badge variant="light">{p.kind}</Badge></Table.Td>
              <Table.Td>{p.programme}</Table.Td>
              <Table.Td>{p.email ?? ""}</Table.Td>
              <Table.Td>{p.office ?? ""}</Table.Td>
              <Table.Td>
                {manage && (
                  <Button size="xs" variant="light" onClick={() => update.mutate({ id: p.id, is_active: !p.is_active })}>
                    {p.is_active ? "Deactivate" : "Activate"}
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </PageBody>
  );
}
