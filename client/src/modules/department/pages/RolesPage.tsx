import { Alert, Badge, Button, List, NumberInput, Select, Stack, Table, TextInput } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAssignTenure, useChangeTenure, useDepartments, useRoleWarnings, useTenures } from "../api/hooks";
import type { Tenure, TenureInput } from "../api/types";
import { PageBody, useDialog } from "../components/PageBody";
import { useCanAct } from "../components/acting";

type Dialog = { kind: "assign"; input: TenureInput } | { kind: "change"; tenure: Tenure; valid_to: string };

const iso = (local: string) => (local ? new Date(local).toISOString() : "");

export default function RolesPage() {
  const can = useCanAct();
  const { data, isPending, error } = useTenures();
  const warnings = useRoleWarnings();
  const { dialog, setDialog, opened } = useDialog<Dialog>();
  const rows = data?.results ?? [];

  return (
    <PageBody
      isPending={isPending} error={error} isEmpty={rows.length === 0} emptyTitle="No HOD or Dept_Admin tenure recorded"
      header={(
        <PageHeader
          title="HOD & Dept_Admin" subtitle="Who holds each department role, and when; headship follows the HOD in effect"
          action={can("department.role_assignment.assign") && (
            <Button onClick={() => setDialog({ kind: "assign",
              input: { department: "", role: "hod", user_id: 0, valid_from: "", valid_to: "" } })}>
              Record tenure
            </Button>
          )}
        />
      )}
      overlays={<TenureDialog dialog={dialog} opened={opened} setDialog={setDialog} />}
    >
      {(warnings.data ?? []).length > 0 && (
        <Alert color="orange" variant="light" title="Roles that need a holder" mb="md">
          <List size="sm">
            {(warnings.data ?? []).map((w) => <List.Item key={`${w.department}-${w.role}`}>{w.message}</List.Item>)}
          </List>
        </Alert>
      )}
      <TenureTable rows={rows} onChange={(t) => setDialog({ kind: "change", tenure: t, valid_to: "" })} />
    </PageBody>
  );
}

function TenureDialog({ dialog, opened, setDialog }: {
  dialog: Dialog | null; opened: boolean; setDialog: (d: Dialog | null) => void;
}) {
  const assign = useAssignTenure();
  const change = useChangeTenure();
  const active = dialog?.kind === "change" ? change : assign;

  function submit() {
    if (!dialog) return;
    const done = { onSuccess: () => setDialog(null) };
    if (dialog.kind === "assign") {
      assign.mutate({ ...dialog.input, valid_from: iso(dialog.input.valid_from), valid_to: iso(dialog.input.valid_to) }, done);
    } else {
      change.mutate({ id: dialog.tenure.id, valid_to: iso(dialog.valid_to) }, done);
    }
  }

  return (
    <FormModal
      opened={opened} onClose={() => setDialog(null)} onSubmit={submit}
      title={dialog?.kind === "change" ? "Change end date" : "Record tenure"}
      submitting={active.isPending} error={active.error}
    >
      {dialog?.kind === "assign" && <AssignFields dialog={dialog} onChange={setDialog} />}
      {dialog?.kind === "change" && (
        <TextInput type="datetime-local" label="New end" value={dialog.valid_to}
          onChange={(e) => setDialog({ ...dialog, valid_to: e.currentTarget.value })} />
      )}
    </FormModal>
  );
}

type AssignDialog = Extract<Dialog, { kind: "assign" }>;

function AssignFields({ dialog, onChange }: { dialog: AssignDialog; onChange: (d: Dialog) => void }) {
  const departments = useDepartments();
  const set = (patch: Partial<TenureInput>) => onChange({ ...dialog, input: { ...dialog.input, ...patch } });
  return (
    <Stack>
      <Select label="Department" value={dialog.input.department || null}
        data={(departments.data ?? []).map((d) => ({ value: d.code, label: `${d.code} — ${d.name}` }))}
        onChange={(v) => set({ department: v ?? "" })} />
      <Select label="Role" allowDeselect={false} value={dialog.input.role}
        data={[{ value: "hod", label: "HOD" }, { value: "dept_admin", label: "Dept_Admin" }]}
        onChange={(v) => set({ role: v === "dept_admin" ? "dept_admin" : "hod" })} />
      <NumberInput label="Employee user id" value={dialog.input.user_id || ""}
        onChange={(v) => set({ user_id: Number(v) || 0 })} />
      <TextInput type="datetime-local" label="Starts" value={dialog.input.valid_from}
        onChange={(e) => set({ valid_from: e.currentTarget.value })} />
      <TextInput type="datetime-local" label="Ends" value={dialog.input.valid_to}
        onChange={(e) => set({ valid_to: e.currentTarget.value })} />
    </Stack>
  );
}

function TenureTable({ rows, onChange }: { rows: Tenure[]; onChange: (t: Tenure) => void }) {
  const can = useCanAct();
  return (
    <Table striped withTableBorder>
      <Table.Thead>
        <Table.Tr><Table.Th>Department</Table.Th><Table.Th>Role</Table.Th><Table.Th>Holder</Table.Th>
          <Table.Th>From</Table.Th><Table.Th>To</Table.Th><Table.Th /><Table.Th /></Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {rows.map((t) => (
          <Table.Tr key={t.id}>
            <Table.Td>{t.department}</Table.Td>
            <Table.Td>{t.role === "hod" ? "HOD" : "Dept_Admin"}</Table.Td>
            <Table.Td>{t.user_id}</Table.Td>
            <Table.Td>{new Date(t.valid_from).toLocaleString()}</Table.Td>
            <Table.Td>{new Date(t.valid_to).toLocaleString()}</Table.Td>
            <Table.Td>{t.in_effect && <Badge color="green">in effect</Badge>}</Table.Td>
            <Table.Td>
              {can("department.role_assignment.assign") && (
                <Button size="xs" variant="light" onClick={() => onChange(t)}>Change end</Button>
              )}
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
