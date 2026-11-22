import { useState } from "react";
import { Alert, Button, Card, Container, Group, Select, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAssignComplaint, useAssignmentQueue, useHandlerOptions } from "../api/hooks";
import type { Complaint } from "../api/types";

export default function AssignmentQueuePage() {
  const complaints = useAssignmentQueue();
  const handlers = useHandlerOptions();
  const assign = useAssignComplaint();
  const [ids, setIds] = useState<Record<string, string>>({});
  const [categories, setCategories] = useState<Record<string, string>>({});
  const [priorities, setPriorities] = useState<Record<string, "low" | "medium" | "high">>({});
  const error = complaints.error ?? handlers.error;
  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;
  const options = (handlers.data ?? []).map((person) => ({
    value: String(person.user_id),
    label: `${person.display_name} · ${person.kind}${person.department ? ` · ${person.department}` : ""}`,
  }));
  return <Container size="lg">
    <PageHeader title="Complaint Assignment" subtitle="Assign active complaints to an employee and set a response priority." />
    <Stack>
      {(complaints.data?.results ?? []).map((row) => <AssignmentCard key={row.reference} complaint={row}
        options={options} assignee={ids[row.reference] ?? ""} priority={priorities[row.reference] ?? (row.priority || "medium")}
        category={categories[row.reference] ?? row.category}
        setAssignee={(value) => setIds((old) => ({ ...old, [row.reference]: value ?? "" }))}
        setCategory={(value) => setCategories((old) => ({ ...old, [row.reference]: value }))}
        setPriority={(value) => value && setPriorities((old) => ({ ...old, [row.reference]: value as "low" | "medium" | "high" }))}
        busy={assign.isPending}
        onAssign={() => assign.mutate({ reference: row.reference, assignee_user_id: Number(ids[row.reference]), category: categories[row.reference] ?? row.category, priority: priorities[row.reference] ?? (row.priority || "medium") }, {
          onSuccess: () => notifications.show({ color: "green", title: "Complaint assigned", message: "The handler and priority were saved." }),
          onError: (e) => notifications.show({ color: "red", title: "Could not assign complaint", message: errorMessage(e) }),
        })} />)}
      {!complaints.isLoading && !complaints.data?.results.length && <Alert color="gray">There are no active complaints to assign.</Alert>}
    </Stack>
  </Container>;
}

function AssignmentCard({ complaint, options, assignee, category, priority, setAssignee, setCategory, setPriority, onAssign, busy }: {
  complaint: Complaint; options: { value: string; label: string }[]; assignee: string;
  category: string; setCategory: (value: string) => void;
  priority: "low" | "medium" | "high"; setAssignee: (value: string | null) => void;
  setPriority: (value: string | null) => void; onAssign: () => void; busy: boolean;
}) {
  const [manualId, setManualId] = useState("");
  return <Card withBorder>
    <Stack>
      <Group justify="space-between"><Text fw={600}>{complaint.category}</Text><Text size="sm">{complaint.status} · {complaint.priority} priority</Text></Group>
      <Text size="xs" c="dimmed">{complaint.reference} · SLA due {complaint.sla_due_at ? new Date(complaint.sla_due_at).toLocaleString() : "not set"}</Text>
      <Text>{complaint.description}</Text>
      <TextInput label="Complaint category/type" value={category} onChange={(event) => setCategory(event.currentTarget.value)} required />
      <Select label="Employee handler" searchable clearable data={options} value={assignee} onChange={setAssignee} />
      <TextInput label="Or enter an employee ID" type="number" value={manualId} onChange={(event) => setManualId(event.currentTarget.value)} onBlur={() => manualId && setAssignee(manualId)} />
      <Select label="Priority" data={["low", "medium", "high"]} value={priority} onChange={setPriority} />
      <Group justify="flex-end"><Button onClick={onAssign} loading={busy} disabled={!assignee || Number.isNaN(Number(assignee))}>Assign and start work</Button></Group>
    </Stack>
  </Card>;
}
