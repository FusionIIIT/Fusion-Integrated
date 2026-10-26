import {
  ActionIcon, Alert, Button, Card, Container, Group, List, Select, Stack, Table, TextInput, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useEffect, useState } from "react";
import { FaTrash } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useHierarchy, useSaveHierarchy } from "../api/hooks";
import type { OrgUnit, SanctionRoute } from "../api/types";

const BLANK_ROUTE: SanctionRoute = { employee_kind: "", category: "", department: "",
  applicant_designation: "", establishment_designation: "", sanction_designation: "" };

/** EL-UC-014 / BR-EL-019: who reviews each unit, and which authority sanctions what. */
export default function HierarchyPage() {
  const { data, error } = useHierarchy();
  const save = useSaveHierarchy();
  const [units, setUnits] = useState<OrgUnit[]>([]);
  const [routes, setRoutes] = useState<SanctionRoute[]>([]);
  const [note, setNote] = useState("");

  useEffect(() => { if (data) { setUnits(data.units); setRoutes(data.routes); } }, [data]);
  if (error) return <Container><ErrorState error={error} /></Container>;
  const heads = data?.choices.unit_head ?? [];
  const estt = data?.choices.establishment ?? [];
  const auth = data?.choices.authority ?? [];
  const setUnit = (i: number, p: Partial<OrgUnit>) => setUnits(units.map((u, j) => j === i ? { ...u, ...p } : u));
  const setRoute = (i: number, p: Partial<SanctionRoute>) =>
    setRoutes(routes.map((r, j) => j === i ? { ...r, ...p } : r));

  return (
    <Container size="xl">
      <PageHeader title="Approval Hierarchy"
        subtitle={data?.revision_id ? `Revision ${data.revision_id} is in effect` : "Not configured"} />
      {!!data?.warnings.length && (
        <Alert color="yellow" mb="md" title="Employees who cannot apply yet">
          <List size="sm">{data.warnings.map((w) => <List.Item key={w}>{w}</List.Item>)}</List>
        </Alert>)}
      <Card padding="lg" mb="lg">
        <Title order={4} mb="sm">Unit Heads</Title>
        <Table>
          <Table.Thead><Table.Tr><Table.Th>Department / section</Table.Th><Table.Th>Unit Head</Table.Th>
            <Table.Th>Reviews the Unit Head's own leave</Table.Th><Table.Th /></Table.Tr></Table.Thead>
          <Table.Tbody>
            {units.map((u, i) => (
              <Table.Tr key={i}>
                <Table.Td><TextInput value={u.department}
                  onChange={(e) => setUnit(i, { department: e.currentTarget.value })} /></Table.Td>
                <Table.Td><Select searchable data={heads} value={u.unit_head_designation || null}
                  onChange={(v) => setUnit(i, { unit_head_designation: v ?? "" })} /></Table.Td>
                <Table.Td><Select searchable clearable data={heads} value={u.head_leave_designation || null}
                  onChange={(v) => setUnit(i, { head_leave_designation: v ?? "" })} /></Table.Td>
                <Table.Td><ActionIcon variant="subtle" color="red" aria-label="Remove"
                  onClick={() => setUnits(units.filter((_, j) => j !== i))}><FaTrash size={11} /></ActionIcon></Table.Td>
              </Table.Tr>))}
          </Table.Tbody>
        </Table>
        <Button mt="sm" size="xs" variant="light" onClick={() => setUnits([...units,
          { department: "", unit_head_designation: "", head_leave_designation: "" }])}>Add unit</Button>
      </Card>
      <Card padding="lg">
        <Title order={4} mb="sm">Higher-sanction routes (SCL, EL, COL, VL)</Title>
        <Table>
          <Table.Thead><Table.Tr><Table.Th>Employees</Table.Th><Table.Th>Category</Table.Th>
            <Table.Th>Department</Table.Th><Table.Th>Applicant holds</Table.Th>
            <Table.Th>Establishment step</Table.Th><Table.Th>Sanctioned by</Table.Th><Table.Th /></Table.Tr></Table.Thead>
          <Table.Tbody>
            {routes.map((r, i) => (
              <Table.Tr key={i}>
                <Table.Td><Select w={110} value={r.employee_kind} onChange={(v) =>
                  setRoute(i, { employee_kind: (v ?? "") as SanctionRoute["employee_kind"] })}
                  data={[{ value: "", label: "Any" }, { value: "faculty", label: "Faculty" },
                    { value: "staff", label: "Staff" }]} /></Table.Td>
                <Table.Td><Select w={90} value={r.category} onChange={(v) => setRoute(i, { category: v ?? "" })}
                  data={[{ value: "", label: "Any" }, "SCL", "EL", "COL", "VL"]} /></Table.Td>
                <Table.Td><TextInput w={140} value={r.department} placeholder="Any"
                  onChange={(e) => setRoute(i, { department: e.currentTarget.value })} /></Table.Td>
                <Table.Td><TextInput w={140} value={r.applicant_designation} placeholder="Any"
                  onChange={(e) => setRoute(i, { applicant_designation: e.currentTarget.value })} /></Table.Td>
                <Table.Td><Select clearable data={estt} value={r.establishment_designation || null}
                  placeholder="None" onChange={(v) => setRoute(i, { establishment_designation: v ?? "" })} /></Table.Td>
                <Table.Td><Select searchable data={auth} value={r.sanction_designation || null}
                  onChange={(v) => setRoute(i, { sanction_designation: v ?? "" })} /></Table.Td>
                <Table.Td><ActionIcon variant="subtle" color="red" aria-label="Remove"
                  onClick={() => setRoutes(routes.filter((_, j) => j !== i))}><FaTrash size={11} /></ActionIcon></Table.Td>
              </Table.Tr>))}
          </Table.Tbody>
        </Table>
        <Button mt="sm" size="xs" variant="light" onClick={() => setRoutes([...routes, BLANK_ROUTE])}>
          Add route</Button>
        <Stack mt="lg">
          <TextInput label="Office order or reason for this revision" value={note}
            onChange={(e) => setNote(e.currentTarget.value)} />
          {save.error != null && <ErrorState error={save.error} />}
          <Group justify="flex-end">
            <Button loading={save.isPending} onClick={() => save.mutate({ units, routes, note }, {
              onSuccess: () => notifications.show({ color: "green", title: "Hierarchy saved",
                message: "New requests and new tasks use it from now." }) })}>
              Save as current hierarchy</Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
