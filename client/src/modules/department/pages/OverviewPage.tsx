import { Badge, Button, Card, Group, Select, Stack, Table, Text, TextInput, Textarea, Title } from "@mantine/core";

import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useDecideChange, useDepartment, useDepartments, useOfficialChanges, useProposeChange, useUpdateDepartment,
} from "../api/hooks";
import type { GeneralUpdate, OfficialChange } from "../api/types";
import { ActionError, PageBody, useDialog } from "../components/PageBody";
import { useCanAct } from "../components/acting";

type Dialog =
  | { kind: "general"; values: GeneralUpdate }
  | { kind: "official"; field: OfficialChange["field"]; value: string };

const GENERAL: { key: keyof GeneralUpdate; label: string }[] = [
  { key: "description", label: "Description" },
  { key: "contact_email", label: "Contact email" },
  { key: "contact_phone", label: "Contact phone" },
  { key: "office_location", label: "Office location" },
  { key: "website", label: "Website" },
];

export default function OverviewPage() {
  const can = useCanAct();
  const list = useDepartments();
  const code = list.data?.[0]?.code;
  const detail = useDepartment(code);
  const changes = useOfficialChanges();
  const update = useUpdateDepartment();
  const propose = useProposeChange();
  const decide = useDecideChange();
  const { dialog: dialog, setDialog: setDialog, opened } = useDialog<Dialog>();
  const dept = detail.data;
  const active = dialog?.kind === "official" ? propose : update;

  function submit() {
    if (!dialog || !code) return;
    const done = { onSuccess: () => setDialog(null) };
    if (dialog.kind === "general") update.mutate({ code, ...dialog.values }, done);
    else propose.mutate({ field: dialog.field, value: dialog.value }, done);
  }

  return (
    <PageBody
      isPending={list.isPending || (!!code && detail.isPending)} error={list.error ?? detail.error}
      isEmpty={!code} emptyTitle="You are not attached to a department in this role"
      header={(
        <PageHeader
          title={dept?.name ?? "Department"} subtitle={dept ? `Code ${dept.code}` : undefined}
          action={dept && (
            <Group>
              {can("department.department.update") && (
                <Button variant="light" onClick={() => setDialog({ kind: "general", values: Object.fromEntries(
                  GENERAL.map((g) => [g.key, dept[g.key]])) as GeneralUpdate })}>Edit details</Button>
              )}
              {can("department.official_change.create") && (
                <Button onClick={() => setDialog({ kind: "official", field: "name", value: dept.name })}>
                  Propose official change
                </Button>
              )}
            </Group>
          )}
        />
      )}
      overlays={(
        <FormModal
          opened={opened} onClose={() => setDialog(null)} onSubmit={submit}
          title={dialog?.kind === "official" ? "Propose official change" : "Edit details"}
          subtitle={dialog?.kind === "official" ? "Takes effect only when the HOD approves it" : undefined}
          submitting={active.isPending} error={active.error}
        >
          {dialog?.kind === "general" && (
            <Stack>
              {GENERAL.map((g) => (
                <TextInput key={g.key} label={g.label} value={dialog.values[g.key] ?? ""}
                  onChange={(e) => setDialog({ ...dialog, values: { ...dialog.values, [g.key]: e.currentTarget.value } })} />
              ))}
            </Stack>
          )}
          {dialog?.kind === "official" && (
            <Stack>
              <Select label="Detail" allowDeselect={false} value={dialog.field}
                data={[{ value: "name", label: "Name" }, { value: "core_policies", label: "Core policies" }]}
                onChange={(v) => setDialog({ ...dialog, field: v === "core_policies" ? "core_policies" : "name" })} />
              <Textarea label="Proposed value" minRows={3} value={dialog.value}
                onChange={(e) => setDialog({ ...dialog, value: e.currentTarget.value })} />
            </Stack>
          )}
        </FormModal>
      )}
    >
      {dept && (
        <Stack>
          <ActionError errors={[decide.error]} />
          <Card withBorder padding="lg">
            <Stack gap="xs">
              <Group gap="xs">
                <Text fw={600}>Head of department:</Text>
                <Text>{dept.headship?.display_name ?? "No HOD in effect"}</Text>
              </Group>
              {dept.description && <Text size="sm">{dept.description}</Text>}
              {GENERAL.filter((g) => g.key !== "description" && dept[g.key]).map((g) => (
                <Text key={g.key} size="sm">{g.label}: {dept[g.key]}</Text>
              ))}
              {dept.programmes.length > 0 && (
                <Group gap="xs">
                  <Text size="sm" fw={600}>Programmes:</Text>
                  {dept.programmes.map((p) => <Badge key={p} variant="light">{p}</Badge>)}
                </Group>
              )}
            </Stack>
          </Card>
          <Card withBorder padding="lg">
            <Title order={5}>Core policies</Title>
            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{dept.core_policies || "None recorded."}</Text>
          </Card>
          {can("department.official_change.view") && (
            <Card withBorder padding="lg">
              <Title order={5} mb="sm">Official changes</Title>
              {(changes.data?.results ?? []).length === 0 ? <Text c="dimmed" size="sm">No proposals.</Text> : (
                <Table>
                  <Table.Tbody>
                    {(changes.data?.results ?? []).map((c) => (
                      <Table.Tr key={c.id}>
                        <Table.Td>{c.field === "name" ? "Name" : "Core policies"}</Table.Td>
                        <Table.Td style={{ whiteSpace: "pre-wrap" }}>{c.proposed_value}</Table.Td>
                        <Table.Td><StatusBadge status={c.status} /></Table.Td>
                        <Table.Td>
                          {c.status === "pending" && can("department.official_change.approve") && (
                            <Group gap="xs">
                              <Button size="xs" onClick={() => decide.mutate({ id: c.id, approve: true })}>Approve</Button>
                              <Button size="xs" color="red" variant="light"
                                onClick={() => decide.mutate({ id: c.id, approve: false })}>Reject</Button>
                            </Group>
                          )}
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          )}
        </Stack>
      )}
    </PageBody>
  );
}
