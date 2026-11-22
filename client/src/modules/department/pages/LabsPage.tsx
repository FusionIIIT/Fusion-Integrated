import { Button, NumberInput, Select, Stack, Table, TextInput, Textarea } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useLabs, useSaveLab } from "../api/hooks";
import type { LabInput } from "../api/types";
import { PageBody, useDialog } from "../components/PageBody";
import { useCanAct } from "../components/acting";

const STATUSES = [
  { value: "available", label: "Available" },
  { value: "maintenance", label: "Under maintenance" },
  { value: "retired", label: "Retired" },
];

export default function LabsPage() {
  const can = useCanAct();
  const { data, isPending, error } = useLabs();
  const save = useSaveLab();
  const { dialog: form, setDialog: setForm, opened } = useDialog<LabInput & { id?: number }>();
  const rows = data?.results ?? [];

  return (
    <PageBody
      isPending={isPending} error={error} isEmpty={rows.length === 0} emptyTitle="No lab resources recorded yet"
      header={(
        <PageHeader
          title="Lab Resources" subtitle="Labs and their equipment, for planning"
          action={can("department.lab_resource.update") && (
            <Button onClick={() => setForm({ name: "", location: "", equipment: "", capacity: null, status: "available" })}>
              Add lab
            </Button>
          )}
        />
      )}
      overlays={(
        <FormModal
          opened={opened} onClose={() => setForm(null)} title={form?.id ? "Edit lab" : "Add lab"}
          onSubmit={() => form && save.mutate(form, { onSuccess: () => setForm(null) })}
          submitting={save.isPending} error={save.error}
        >
          {form && (
            <Stack>
              <TextInput label="Name" value={form.name ?? ""} onChange={(e) => setForm({ ...form, name: e.currentTarget.value })} />
              <TextInput label="Location" value={form.location ?? ""}
                onChange={(e) => setForm({ ...form, location: e.currentTarget.value })} />
              <Textarea label="Equipment" value={form.equipment ?? ""}
                onChange={(e) => setForm({ ...form, equipment: e.currentTarget.value })} />
              <NumberInput label="Capacity" min={0} value={form.capacity ?? ""}
                onChange={(v) => setForm({ ...form, capacity: typeof v === "number" ? v : null })} />
              <Select label="Status" allowDeselect={false} data={STATUSES} value={form.status ?? "available"}
                onChange={(v) => setForm({ ...form, status: (v ?? "available") as LabInput["status"] })} />
            </Stack>
          )}
        </FormModal>
      )}
    >
      <Table striped withTableBorder>
        <Table.Thead>
          <Table.Tr><Table.Th>Lab</Table.Th><Table.Th>Location</Table.Th><Table.Th>Equipment</Table.Th>
            <Table.Th>Capacity</Table.Th><Table.Th>Status</Table.Th><Table.Th /></Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((lab) => (
            <Table.Tr key={lab.id}>
              <Table.Td>{lab.name}</Table.Td>
              <Table.Td>{lab.location}</Table.Td>
              <Table.Td style={{ whiteSpace: "pre-wrap" }}>{lab.equipment}</Table.Td>
              <Table.Td>{lab.capacity ?? "—"}</Table.Td>
              <Table.Td><StatusBadge status={lab.status} /></Table.Td>
              <Table.Td>
                {can("department.lab_resource.update") && (
                  <Button size="xs" variant="light" onClick={() => setForm({ ...lab })}>Edit</Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </PageBody>
  );
}
