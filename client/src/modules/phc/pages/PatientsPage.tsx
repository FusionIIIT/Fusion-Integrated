import { useState } from "react";
import { Button, Container, NumberInput, Stack, Table, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePatients, usePhcPost } from "../api";

export default function PatientsPage() {
  const { can, session } = useAuth();
  const [query, setQuery] = useState("");
  const { data, isPending, error } = usePatients(query);
  const [userId, setUserId] = useState<number | "">(session?.user.id ?? "");
  const register = usePhcPost("/phc/patients");
  if (error) return <Container><ErrorState error={error} /></Container>;
  const submit = async () => {
    try { await register.mutateAsync(userId === session?.user.id ? {} : { user_id: userId });
      notifications.show({ message: "Patient registered", color: "green" }); }
    catch (e) { notifications.show({ message: errorMessage(e), color: "red" }); }
  };
  const rows = data?.results ?? [];
  return <Container size="lg"><PageHeader title="Patients" subtitle="Institute members registered with the Health Center" />
    <TextInput label="Search patient number or institute user ID" value={query}
      onChange={(e) => setQuery(e.currentTarget.value)} mb="md" />
    {(can("phc.patient.register_self") || can("phc.patient.register")) && <Stack mb="lg" maw={420}>
      {can("phc.patient.register") && <NumberInput label="Institute user ID" value={userId}
        onChange={(value) => setUserId(typeof value === "number" ? value : "")} min={1} />}
      <Button onClick={submit} loading={register.isPending}>Register patient</Button>
    </Stack>}
    {isPending ? <Text c="dimmed">Loading patients…</Text> : rows.length === 0 ?
      <Text c="dimmed">No patient records yet.</Text> : <Table.ScrollContainer minWidth={560}><Table striped>
        <Table.Thead><Table.Tr><Table.Th>Patient number</Table.Th><Table.Th>Institute user ID</Table.Th><Table.Th>Registered</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{rows.map((p) => <Table.Tr key={p.id}><Table.Td>{p.patient_number}</Table.Td>
          <Table.Td>{p.user_id}</Table.Td><Table.Td>{new Date(p.created_at).toLocaleDateString()}</Table.Td></Table.Tr>)}</Table.Tbody>
      </Table></Table.ScrollContainer>}
  </Container>;
}
