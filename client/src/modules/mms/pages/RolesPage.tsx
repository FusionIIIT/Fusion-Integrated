import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Select, Stack, Table,
  Text, TextInput,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMmsAction, useMmsData } from "../api";

interface Employee {
  user_id: number;
  username: string;
  display_name: string;
  kind: string;
  email: string;
}

interface Assignment {
  id: number;
  role: "caretaker" | "warden";
  user_id: number;
  starts_at: string;
  ends_at: string;
  is_current: boolean;
  employee?: Employee | null;
}

interface RoleResponse {
  current: Assignment[];
  history: Assignment[];
  employees: Employee[];
}

export default function RolesPage() {
  const { can } = useAuth();
  const allowed = can("mess_management.roles.manage");
  const assignments = useMmsData<RoleResponse>("roles", allowed);
  const save = useMmsAction("roles");
  const [role, setRole] = useState<string | null>("caretaker");
  const [employee, setEmployee] = useState<string | null>(null);
  const [endsAt, setEndsAt] = useState("");

  if (!allowed) {
    return <Container size="lg"><PageHeader title="Mess Role Management" />
      <Alert color="gray">Role assignment is restricted to Mess Admin.</Alert>
    </Container>;
  }
  if (assignments.error) {
    return <Container size="lg"><PageHeader title="Mess Role Management" />
      <ErrorState error={assignments.error} />
    </Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="Mess Role Management"
        subtitle="Assign institutional employees for a time-bound Caretaker or Warden term" />
      {assignments.isPending && <Alert color="blue">Loading assignments and directory employees…</Alert>}
      <Card withBorder mb="lg">
        <Stack>
          <Select label="Mess role" value={role} onChange={setRole}
            data={[{ value: "caretaker", label: "Mess Caretaker" },
              { value: "warden", label: "Mess Warden" }]} />
          <Select label="Institute employee" value={employee} onChange={setEmployee}
            searchable
            data={(assignments.data?.employees ?? []).map((person) => ({
              value: String(person.user_id),
              label: `${person.display_name} (${person.username}) · ${person.kind}`,
            }))} />
          <TextInput type="datetime-local" label="Assignment ends at"
            description="The assignment takes effect immediately and ends at this time."
            value={endsAt} onChange={(event) => setEndsAt(event.currentTarget.value)} />
          <Group>
            <Button loading={save.isPending} disabled={!role || !employee || !endsAt}
              onClick={() => save.mutate({ body: {
                role, user_id: Number(employee), ends_at: endsAt,
              } })}>Assign / reassign role</Button>
          </Group>
          <Text size="xs" c="dimmed">
            Reassignment immediately transfers active authority and pending work to the new Caretaker.
          </Text>
        </Stack>
      </Card>

      <Card withBorder mb="lg">
        <Text fw={600} mb="sm">Current assignments</Text>
        {!assignments.data?.current.length &&
          <Alert color="yellow">No active assignment is currently recorded for these roles.</Alert>}
        <Table>
          <Table.Thead><Table.Tr><Table.Th>Role</Table.Th>
            <Table.Th>Employee</Table.Th><Table.Th>Starts</Table.Th>
            <Table.Th>Ends</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>{(assignments.data?.current ?? []).map((row) => (
            <Table.Tr key={row.id}>
              <Table.Td>{row.role === "caretaker" ? "Mess Caretaker" : "Mess Warden"}</Table.Td>
              <Table.Td>{row.employee?.display_name ?? row.user_id}</Table.Td>
              <Table.Td>{new Date(row.starts_at).toLocaleString()}</Table.Td>
              <Table.Td>{new Date(row.ends_at).toLocaleString()}</Table.Td>
            </Table.Tr>
          ))}</Table.Tbody>
        </Table>
      </Card>

      <Card withBorder>
        <Text fw={600} mb="sm">Assignment history</Text>
        {!assignments.data?.history.length &&
          <Text size="sm" c="dimmed">No assignment history yet.</Text>}
        <Stack>
          {(assignments.data?.history ?? []).map((row) => (
            <Group key={row.id} justify="space-between">
              <Text size="sm">{row.role} · {row.employee?.display_name ?? row.user_id}</Text>
              <Group>
                <Badge color={row.is_current ? "green" : "gray"}>
                  {row.is_current ? "Current" : "Ended"}
                </Badge>
                <Text size="xs" c="dimmed">
                  {new Date(row.starts_at).toLocaleString()} – {new Date(row.ends_at).toLocaleString()}
                </Text>
              </Group>
            </Group>
          ))}
        </Stack>
      </Card>
    </Container>
  );
}
