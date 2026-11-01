import {
  Badge, Button, Card, Container, Group, NumberInput, Select, Stack, Table,
  Text, Textarea, TextInput, Title,
} from "@mantine/core";
import { useState } from "react";

import { http } from "../../../lib/http";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

type Props = { tasksOnly?: boolean; adminOnly?: boolean };
type Leave = {
  id: number; category: string; start_date: string; end_date: string;
  purpose: string; state: string; chargeable_days: string; substitute_user_id?: number | null;
};
type Balance = { category: string; year: number; balance: string; carried: string };

const leaveStates: Record<string, string> = {
  awaiting_substitute: "Awaiting substitute",
  applicant_action: "Applicant action required",
  unit_head_review: "Unit Head review",
  establishment_routing: "Establishment routing",
  final_sanction: "Final sanction",
  director_self_sanction: "Director self-sanction",
  approved: "Approved", rejected: "Rejected", withdrawn: "Withdrawn",
  cancelled: "Cancelled", resumption_review: "Resumption review",
};
const pendingStates = [
  "awaiting_substitute", "applicant_action", "unit_head_review", "establishment_routing",
  "final_sanction", "director_self_sanction",
];

export default function LeavePage({ tasksOnly = false, adminOnly = false }: Props) {
  const qc = useQueryClient();
  const [category, setCategory] = useState("CL");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [half, setHalf] = useState("");
  const [purpose, setPurpose] = useState("");
  const [substitute, setSubstitute] = useState<number | "">("");
  const [actionId, setActionId] = useState<number | null>(null);
  const [extensionStart, setExtensionStart] = useState("");
  const [extensionEnd, setExtensionEnd] = useState("");
  const [resumptionDate, setResumptionDate] = useState("");
  const [policyYear, setPolicyYear] = useState(new Date().getFullYear());
  const [policyValues, setPolicyValues] = useState('{"entitlements": {}}');
  const [policyHierarchy, setPolicyHierarchy] = useState("{}");
  const [calendarYear, setCalendarYear] = useState(new Date().getFullYear());
  const [calendarVersion, setCalendarVersion] = useState(1);
  const [calendarHolidays, setCalendarHolidays] = useState("[]");
  const [offlineEmployee, setOfflineEmployee] = useState<number | "">("");
  const [offlineStart, setOfflineStart] = useState("");
  const [offlineEnd, setOfflineEnd] = useState("");
  const [offlineEvidence, setOfflineEvidence] = useState("");
  const [adminMessage, setAdminMessage] = useState("");
  const applications = useQuery({
    queryKey: ["leave", tasksOnly ? "tasks" : "mine"],
    queryFn: async () => (await http.get<{ results: Leave[] }>("/leave/applications")).data,
  });
  const balances = useQuery({
    queryKey: ["leave", "balances"],
    queryFn: async () => (await http.get<Balance[]>("/leave/balances")).data,
    enabled: !tasksOnly && !adminOnly,
  });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["leave"] });

  const submit = useMutation({
    mutationFn: () => http.post("/leave/applications", {
      category, start_date: start, end_date: end, half,
      purpose, ...(substitute === "" ? {} : { substitute_user_id: substitute }),
    }),
    onSuccess: () => { invalidate(); setPurpose(""); setSubstitute(""); },
  });
  const decide = useMutation({
    mutationFn: ({ id, outcome, recommendation }: {
      id: number; outcome: string; recommendation?: string;
    }) => http.post(`/leave/applications/${id}/decision`, {
      outcome, recommendation, reason: "",
    }),
    onSuccess: invalidate,
  });
  const withdraw = useMutation({
    mutationFn: (id: number) => http.post(`/leave/applications/${id}/withdraw`, {}),
    onSuccess: invalidate,
  });
  const action = useMutation({
    mutationFn: ({ id, path, data }: { id: number; path: string; data?: object }) =>
      http.post(`/leave/applications/${id}/${path}`, data ?? {}),
    onSuccess: () => { invalidate(); setActionId(null); },
  });
  const savePolicy = useMutation({
    mutationFn: () => http.post("/leave/configuration/policies", {
      year: policyYear, values: JSON.parse(policyValues), hierarchy: JSON.parse(policyHierarchy),
    }),
    onSuccess: () => { invalidate(); setAdminMessage("Policy saved."); },
  });
  const saveCalendar = useMutation({
    mutationFn: () => http.post("/leave/configuration/calendars", {
      year: calendarYear, version: calendarVersion, holidays: JSON.parse(calendarHolidays), published: false,
    }),
    onSuccess: () => { invalidate(); setAdminMessage("Calendar saved. Publish it to make it effective."); },
  });
  const runYearEnd = useMutation({
    mutationFn: () => http.post("/leave/year-end", { year: new Date().getFullYear() }),
    onSuccess: () => { invalidate(); setAdminMessage("Year-end processing completed."); },
  });
  const recordOffline = useMutation({
    mutationFn: () => http.post("/leave/admin/offline", {
      employee_user_id: offlineEmployee, employee_kind: "staff", category: "CL",
      start_date: offlineStart, end_date: offlineEnd, purpose: "Offline sanctioned leave",
      evidence: { reference: offlineEvidence },
    }),
    onSuccess: () => { invalidate(); setAdminMessage("Offline leave recorded."); },
  });

  if (adminOnly) {
    return <Container size="lg">
      <Title order={2} mt="xl">Leave administration</Title>
      {adminMessage && <Text c="teal" mt="sm">{adminMessage}</Text>}
      <Card withBorder mt="lg"><Title order={4}>Current policy</Title><Stack mt="md">
        <NumberInput label="Year" value={policyYear} onChange={(value) => setPolicyYear(typeof value === "number" ? value : new Date().getFullYear())} />
        <Textarea label="Policy values JSON" value={policyValues} onChange={(event) => setPolicyValues(event.currentTarget.value)} minRows={4} />
        <Textarea label="Hierarchy JSON" value={policyHierarchy} onChange={(event) => setPolicyHierarchy(event.currentTarget.value)} minRows={3} />
        <Button onClick={() => savePolicy.mutate()} loading={savePolicy.isPending}>Save policy</Button>
      </Stack></Card>
      <Card withBorder mt="lg"><Title order={4}>Holiday / RH calendar</Title><Stack mt="md">
        <Group grow><NumberInput label="Year" value={calendarYear} onChange={(value) => setCalendarYear(typeof value === "number" ? value : new Date().getFullYear())} />
          <NumberInput label="Version" value={calendarVersion} onChange={(value) => setCalendarVersion(typeof value === "number" ? value : 1)} /></Group>
        <Textarea label="Holiday entries JSON" value={calendarHolidays} onChange={(event) => setCalendarHolidays(event.currentTarget.value)} minRows={4} />
        <Button onClick={() => saveCalendar.mutate()} loading={saveCalendar.isPending}>Save calendar</Button>
      </Stack></Card>
      <Card withBorder mt="lg"><Title order={4}>Offline sanctioned leave</Title><Stack mt="md">
        <NumberInput label="Employee user ID" value={offlineEmployee} onChange={(value) => setOfflineEmployee(typeof value === "number" ? value : "")} />
        <Group grow><TextInput label="Start date" type="date" value={offlineStart} onChange={(event) => setOfflineStart(event.currentTarget.value)} />
          <TextInput label="End date" type="date" value={offlineEnd} onChange={(event) => setOfflineEnd(event.currentTarget.value)} /></Group>
        <TextInput label="Sanction/reference evidence" value={offlineEvidence} onChange={(event) => setOfflineEvidence(event.currentTarget.value)} />
        <Button onClick={() => recordOffline.mutate()} loading={recordOffline.isPending} disabled={!offlineEmployee || !offlineStart || !offlineEnd || !offlineEvidence}>Record offline leave</Button>
      </Stack></Card>
      <Card withBorder mt="lg" mb="xl"><Group justify="space-between"><div><Title order={4}>Year-end processing</Title><Text c="dimmed" size="sm">Lapse CL/RH/SCL, carry EL/COL, and convert faculty VL.</Text></div>
        <Button color="orange" onClick={() => runYearEnd.mutate()} loading={runYearEnd.isPending}>Run year end</Button></Group></Card>
    </Container>;
  }

  const rows = applications.data?.results ?? [];
  return <Container size="lg">
    <Title order={2} mt="xl">{tasksOnly ? "Leave tasks" : "Employee Leave"}</Title>
    {!tasksOnly && <>
      <Group align="stretch" mt="lg">
        {(balances.data ?? []).map((balance) => <Card key={balance.category} withBorder p="sm">
          <Text size="xs" c="dimmed">{balance.category} · {balance.year}</Text>
          <Text fw={700} size="lg">{balance.balance} days</Text>
        </Card>)}
      </Group>
      <Card withBorder mt="lg">
        <Title order={4}>New application</Title>
        <Stack mt="md">
          <Select label="Category" data={["CL", "RH", "SCL", "EL", "COL", "VL"]}
            value={category} onChange={(value) => setCategory(value ?? "CL")} />
          {category === "CL" && <Select label="Half day (optional)" clearable
            data={[{ value: "first", label: "First half" }, { value: "second", label: "Second half" }]}
            value={half || null} onChange={(value) => setHalf(value ?? "")} />}
          <Group grow>
            <input aria-label="Start date" type="date" value={start}
              onChange={(event) => setStart(event.currentTarget.value)} />
            <input aria-label="End date" type="date" value={end}
              onChange={(event) => setEnd(event.currentTarget.value)} />
          </Group>
          <NumberInput label="Substitute user id (optional)" value={substitute}
            onChange={(value) => setSubstitute(typeof value === "number" ? value : "")} />
          <Textarea label="Purpose / reason" value={purpose}
            onChange={(event) => setPurpose(event.currentTarget.value)} />
          <Button onClick={() => submit.mutate()} loading={submit.isPending}
            disabled={!start || !end || !purpose}>Submit application</Button>
        </Stack>
      </Card>
    </>}
    <Card withBorder mt="lg">
      <Title order={4}>{tasksOnly ? "Assigned requests" : "My leave history"}</Title>
      <Table mt="md" striped highlightOnHover>
        <Table.Thead><Table.Tr><Table.Th>Category</Table.Th><Table.Th>Period</Table.Th>
          <Table.Th>Status</Table.Th><Table.Th>Days</Table.Th><Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
        <Table.Tbody>{rows.map((row) => <Table.Tr key={row.id}>
          <Table.Td>{row.category}</Table.Td>
          <Table.Td>{row.start_date} to {row.end_date}</Table.Td>
          <Table.Td><Badge>{leaveStates[row.state] ?? row.state}</Badge></Table.Td>
          <Table.Td>{row.chargeable_days}</Table.Td>
          <Table.Td><Group gap="xs">
            {tasksOnly && row.state === "awaiting_substitute" && <>
              <Button size="xs" onClick={() => action.mutate({ id: row.id, path: "substitute", data: { accept: true } })}>Accept</Button>
              <Button size="xs" color="red" onClick={() => action.mutate({ id: row.id, path: "substitute", data: { accept: false } })}>Decline</Button>
            </>}
            {tasksOnly && row.state === "unit_head_review" && row.category in { CL: 1, RH: 1 } && <>
              <Button size="xs" onClick={() => decide.mutate({ id: row.id, outcome: "approve" })}>Approve</Button>
              <Button size="xs" color="red" onClick={() => decide.mutate({ id: row.id, outcome: "reject" })}>Reject</Button>
            </>}
            {tasksOnly && row.state === "unit_head_review" && !(row.category in { CL: 1, RH: 1 }) && <>
              <Button size="xs" onClick={() => decide.mutate({ id: row.id, outcome: "approve", recommendation: "recommended" })}>Recommend</Button>
              <Button size="xs" color="orange" onClick={() => decide.mutate({ id: row.id, outcome: "approve", recommendation: "not_recommended" })}>Not recommend</Button>
            </>}
            {tasksOnly && ["final_sanction", "director_self_sanction"].includes(row.state) && <>
              <Button size="xs" onClick={() => decide.mutate({ id: row.id, outcome: "approve" })}>Sanction</Button>
              <Button size="xs" color="red" onClick={() => decide.mutate({ id: row.id, outcome: "reject" })}>Reject</Button>
            </>}
            {!tasksOnly && pendingStates.includes(row.state) &&
              <Button size="xs" color="red" variant="light" onClick={() => withdraw.mutate(row.id)}>Withdraw</Button>}
            {!tasksOnly && row.state === "approved" && row.start_date > new Date().toISOString().slice(0, 10) &&
              <Button size="xs" color="orange" variant="light" onClick={() => action.mutate({ id: row.id, path: "cancel" })}>Request cancellation</Button>}
            {!tasksOnly && row.state === "approved" && ["EL", "COL", "VL"].includes(row.category) &&
              <Button size="xs" variant="light" onClick={() => setActionId(actionId === row.id ? null : row.id)}>More</Button>}
            <Button component="a" size="xs" variant="subtle" href={`/api/v1/leave/applications/${row.id}/export`}>Export</Button>
            {actionId === row.id && <Stack mt="xs"><Group grow>
              <TextInput aria-label="Extension start" type="date" value={extensionStart} onChange={(event) => setExtensionStart(event.currentTarget.value)} />
              <TextInput aria-label="Extension end" type="date" value={extensionEnd} onChange={(event) => setExtensionEnd(event.currentTarget.value)} />
            </Group><Button size="xs" onClick={() => action.mutate({ id: row.id, path: "extend", data: { start_date: extensionStart, end_date: extensionEnd, purpose: "Extension" } })} disabled={!extensionStart || !extensionEnd}>Request extension</Button>
              <TextInput aria-label="Actual resumption date" type="date" value={resumptionDate} onChange={(event) => setResumptionDate(event.currentTarget.value)} />
              <Button size="xs" onClick={() => action.mutate({ id: row.id, path: "resumption", data: { actual_date: resumptionDate, details: "Resumption submitted" } })} disabled={!resumptionDate}>Submit resumption</Button>
            </Stack>}
          </Group></Table.Td>
        </Table.Tr>)}</Table.Tbody>
      </Table>
    </Card>
  </Container>;
}
