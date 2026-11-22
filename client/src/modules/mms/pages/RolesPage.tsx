import { useState } from "react";
import { Button, Card, Container, Group, Select, Stack, Text, TextInput } from "@mantine/core";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { errorMessage, http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

interface Assignment { readonly id: number; readonly role: string; readonly user_id: number; readonly starts_at: string; readonly ends_at: string | null }

export default function RolesPage() {
  const client = useQueryClient();
  const [role, setRole] = useState<string | null>("caretaker");
  const [userId, setUserId] = useState("");
  const [endsAt, setEndsAt] = useState("");
  const assignments = useQuery({ queryKey: ["mms", "roles"], queryFn: async () => (await http.get<Assignment[]>("/mms/roles/")).data });
  const assign = useMutation({ mutationFn: async () => http.post("/mms/roles/", { role, user_id: Number(userId), ends_at: endsAt ? new Date(endsAt).toISOString() : null }), onSuccess: () => client.invalidateQueries({ queryKey: ["mms", "roles"] }) });
  if (assignments.error) return <Container size="md"><ErrorState error={assignments.error} /></Container>;
  return <Container size="md"><PageHeader title="Mess role assignments" subtitle="Assignments take effect immediately and hand off active duties" />
    <Card withBorder mb="md"><Stack><Group align="end"><Select label="Role" value={role} onChange={setRole} data={[{ value: "caretaker", label: "Mess Caretaker" }, { value: "warden", label: "Mess Warden" }]} />
      <TextInput type="number" label="Institute employee ID" value={userId} onChange={(event) => setUserId(event.currentTarget.value)} />
      <TextInput type="datetime-local" label="Assignment ends" value={endsAt} onChange={(event) => setEndsAt(event.currentTarget.value)} />
      <Button disabled={!role || !userId || assign.isPending} onClick={() => assign.mutate()}>Assign role</Button></Group>
      {assign.error && <Text c="red">{errorMessage(assign.error)}</Text>}</Stack></Card>
    <Stack>{assignments.data?.map((row) => <Card withBorder key={row.id}><Text fw={600}>{row.role === "caretaker" ? "Mess Caretaker" : "Mess Warden"} · employee {row.user_id}</Text>
      <Text size="sm" c="dimmed">{new Date(row.starts_at).toLocaleString()} – {row.ends_at ? new Date(row.ends_at).toLocaleString() : "no end set"}</Text></Card>)}</Stack>
  </Container>;
}
