import { useState } from "react";
import { Alert, Button, Card, Container, Group, NumberInput, Select, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAssignRole, useRoleAssignments } from "../api/hooks";

export default function RoleAssignmentPage() {
  const { data: assignments, isLoading, error } = useRoleAssignments();
  const assign = useAssignRole();

  const [designation, setDesignation] = useState<"caretaker" | "warden">("caretaker");
  const [employeeUserId, setEmployeeUserId] = useState<number | string>("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveUntil, setEffectiveUntil] = useState("");

  const handleAssign = (e: React.FormEvent) => {
    e.preventDefault();
    if (!employeeUserId || !effectiveFrom) return;

    assign.mutate(
      {
        designation,
        employee_user_id: Number(employeeUserId),
        effective_from: effectiveFrom,
        effective_until: effectiveUntil || null,
      },
      {
        onSuccess: () => {
          notifications.show({ color: "green", title: "Role Assigned", message: `Active ${designation} assigned successfully.` });
          setEmployeeUserId("");
          setEffectiveFrom("");
          setEffectiveUntil("");
        },
        onError: (err) => notifications.show({ color: "red", title: "Failed", message: errorMessage(err) }),
      }
    );
  };

  if (error) {
    return <Container size="lg"><ErrorState error={error} /></Container>;
  }

  return (
    <Container size="lg">
      <PageHeader title="MMS Role Assignment (Mess Admin)" />
      <Stack gap="lg">
        <Card withBorder padding="md">
          <form onSubmit={handleAssign}>
            <Stack gap="sm">
              <Text fw={600}>Assign Active Role</Text>
              <Text size="sm" c="dimmed">Exactly one active Caretaker and one active Warden at a time. Mid-cycle reassignments take immediate effect.</Text>
              <Group grow>
                <Select
                  label="Designation"
                  required
                  value={designation}
                  onChange={(val) => setDesignation(val as "caretaker" | "warden")}
                  data={[
                    { value: "caretaker", label: "Mess Caretaker" },
                    { value: "warden", label: "Mess Warden" },
                  ]}
                />
                <NumberInput label="Employee User ID" placeholder="e.g. 1002" required value={employeeUserId} onChange={setEmployeeUserId} />
              </Group>
              <Group grow>
                <TextInput label="Effective From" type="datetime-local" required value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.currentTarget.value)} />
                <TextInput label="Effective Until (Optional)" type="datetime-local" value={effectiveUntil} onChange={(e) => setEffectiveUntil(e.currentTarget.value)} />
              </Group>
              <Group justify="flex-end">
                <Button type="submit" loading={assign.isPending}>Assign Role</Button>
              </Group>
            </Stack>
          </form>
        </Card>

        <Card withBorder padding="md">
          <Text fw={600} mb="sm">Role Assignment History</Text>
          {isLoading ? (
            <Text c="dimmed">Loading roles...</Text>
          ) : !assignments || assignments.length === 0 ? (
            <Alert color="gray">No role assignments on record.</Alert>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Designation</Table.Th>
                  <Table.Th>Employee User ID</Table.Th>
                  <Table.Th>Effective From</Table.Th>
                  <Table.Th>Effective Until</Table.Th>
                  <Table.Th>Active</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {assignments.map((a) => (
                  <Table.Tr key={a.id}>
                    <Table.Td>#{a.id}</Table.Td>
                    <Table.Td style={{ textTransform: "capitalize" }}>{a.designation}</Table.Td>
                    <Table.Td>{a.employee_user_id}</Table.Td>
                    <Table.Td>{new Date(a.effective_from).toLocaleString()}</Table.Td>
                    <Table.Td>{a.effective_until ? new Date(a.effective_until).toLocaleString() : "Indefinite"}</Table.Td>
                    <Table.Td><StatusBadge status={a.is_active ? "active" : "closed"} /></Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}
