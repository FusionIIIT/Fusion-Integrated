import {
  Badge, Button, Card, Container, Group, Select, Stack, Table, Text,
  TextInput, Textarea, Title,
} from "@mantine/core";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";

type Props = { tasksOnly?: boolean };
type Complaint = { id: number; title: string; location: string; state: string; urgent: boolean };

const stateLabels: Record<string, string> = {
  submitted: "Submitted",
  assigned: "Assigned",
  assessed: "Assessed",
  low_cost_review: "Low-cost review",
  committee_review: "Committee review",
  department_head_review: "Department Head review",
  director_review: "Director review",
  estimate_approved: "Estimate approved",
  materials_pending: "Materials pending",
  in_progress: "In progress",
  verification_pending: "Verification pending",
  resolved: "Resolved",
  rejected: "Rejected",
};

const stateColors: Record<string, string> = {
  resolved: "teal",
  rejected: "red",
  in_progress: "blue",
  verification_pending: "violet",
};

export default function IwdPage({ tasksOnly = false }: Props) {
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [issueCategory, setIssueCategory] = useState<string | null>("other");
  const [urgency, setUrgency] = useState<string | null>("normal");
  const [stateFilter, setStateFilter] = useState<string | null>(null);
  const complaints = useQuery({
    queryKey: ["iwd", tasksOnly ? "tasks" : "complaints"],
    queryFn: async () => (await http.get<{ results: Complaint[] }>("/iwd/complaints")).data,
  });
  const submit = useMutation({
    mutationFn: () => http.post("/iwd/complaints", {
      title, location, description, issue_category: issueCategory, urgency,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["iwd"] });
      setTitle(""); setLocation(""); setDescription("");
      setIssueCategory("other"); setUrgency("normal");
    },
  });
  const rows = complaints.data?.results?.filter((row) => !stateFilter || row.state === stateFilter) ?? [];

  return <Container size="lg">
    <Group justify="space-between" mt="xl">
      <div>
        <Title order={2}>{tasksOnly ? "IWD tasks" : "Infrastructure and Works"}</Title>
        <Text c="dimmed" mt={4}>Maintenance complaints, approvals, and repair progress.</Text>
      </div>
      <Badge size="lg" variant="light">{complaints.data?.results?.length ?? 0} total</Badge>
    </Group>
    {!tasksOnly && <Card withBorder mt="lg" radius="md"><Stack>
      <Title order={4}>Report a maintenance issue</Title>
      <Group grow>
        <TextInput label="Issue title" placeholder="e.g. Water leakage" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
        <TextInput label="Location" placeholder="Building / room" value={location} onChange={(e) => setLocation(e.currentTarget.value)} />
      </Group>
      <Group grow>
        <Select
          label="Issue category"
          value={issueCategory}
          onChange={setIssueCategory}
          data={[{ value: "civil", label: "Civil" }, { value: "electrical", label: "Electrical" }, { value: "other", label: "Other" }]}
        />
        <Select
          label="Urgency"
          value={urgency}
          onChange={setUrgency}
          data={["low", "normal", "high", "critical"]}
        />
      </Group>
      <Textarea label="Description" placeholder="Describe the issue and its impact" value={description} onChange={(e) => setDescription(e.currentTarget.value)} minRows={3} />
      <Group justify="flex-end">
        <Button onClick={() => submit.mutate()} loading={submit.isPending} disabled={!title.trim() || !location.trim() || !description.trim()}>Submit complaint</Button>
      </Group>
    </Stack></Card>}
    <Card withBorder mt="lg" radius="md">
      <Group justify="space-between">
        <Title order={4}>{tasksOnly ? "Assigned tasks" : "My complaints"}</Title>
        <Select
          placeholder="Filter by status"
          clearable
          w={210}
          value={stateFilter}
          onChange={setStateFilter}
          data={Object.entries(stateLabels).map(([value, label]) => ({ value, label }))}
        />
      </Group>
      <Table.ScrollContainer minWidth={650} mt="md">
        <Table striped highlightOnHover>
          <Table.Thead><Table.Tr><Table.Th>Issue</Table.Th><Table.Th>Location</Table.Th><Table.Th>Status</Table.Th><Table.Th>Priority</Table.Th></Table.Tr></Table.Thead>
          <Table.Tbody>
            {rows.map((row) => <Table.Tr key={row.id}>
              <Table.Td><Text fw={500}>{row.title}</Text><Text size="xs" c="dimmed">IWD-{row.id}</Text></Table.Td>
              <Table.Td>{row.location}</Table.Td>
              <Table.Td><Badge color={stateColors[row.state] ?? "gray"} variant="light">{stateLabels[row.state] ?? row.state}</Badge></Table.Td>
              <Table.Td>{row.urgent ? <Badge color="orange">Urgent</Badge> : <Text size="sm" c="dimmed">Normal</Text>}</Table.Td>
            </Table.Tr>)}
            {!rows.length && <Table.Tr><Table.Td colSpan={4}><Text ta="center" c="dimmed" py="xl">No complaints match this filter.</Text></Table.Td></Table.Tr>}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Card>
  </Container>;
}
