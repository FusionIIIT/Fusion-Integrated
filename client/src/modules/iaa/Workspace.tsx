import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Anchor, Badge, Button, Container, Group, Loader, Modal, Paper,
  Select, SimpleGrid, Stack, Table, Tabs, Text, Textarea, TextInput, Title } from "@mantine/core";
import { useAuth } from "../../auth/AuthProvider";
import { saveBlob } from "../../lib/download";
import { errorMessage, http, readBlobError } from "../../lib/http";
import { authorities, evidenceLinks, get, headers, label, post, requestActions,
  type RequestRow, type Row } from "./api";
import ConfigPanel from "./ConfigPanel";

interface Pending { path: string; title: string; body: Record<string, unknown>;
  field?: string; evidence?: boolean; }
const currency = (value: unknown) => value == null ? "—" : new Intl.NumberFormat("en-IN", {
  style: "currency", currency: "INR" }).format(Number(value));
const when = (value: unknown) => value ? new Date(String(value)).toLocaleString() : "—";
function Status({ value }: { value: string }) {
  return <Badge variant="light" color={value === "rejected" ? "red" : ["recorded", "closed", "resolved"].includes(value) ? "green" : "blue"}>{label(value)}</Badge>;
}
function Links({ values }: { values: unknown }) {
  return <Stack gap={4}>{Array.isArray(values) && values.map((v, i) => <Anchor key={i}
    href={String(v)} target="_blank" rel="noopener noreferrer">Evidence {i + 1}</Anchor>)}</Stack>;
}

export default function Workspace() {
  const { session: fusion } = useAuth();
  const userId = fusion?.user.id ?? 0;
  const qc = useQueryClient();
  const [role, setRole] = useState(() => sessionStorage.getItem(`iaa-role:${userId}`) ?? "");
  const [tab, setTab] = useState<string | null>(() =>
    new URLSearchParams(window.location.search).get("tab") === "notifications" ? "notifications" : "requests");
  const [selected, setSelected] = useState<number | null>(null);
  const [editor, setEditor] = useState<Record<string, string> | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [remarks, setRemarks] = useState("");
  const [evidence, setEvidence] = useState("");
  const session = useQuery({ queryKey: ["iaa-session", userId], queryFn: () =>
    get<{ roles: { role: string; department: string }[]; user_id: number }>("session", "") });
  const assigned = [...new Set(session.data?.roles.map(r => r.role) ?? [])];
  const active = assigned.includes(role) ? role : assigned.length === 1 ? (assigned[0] ?? "") : "";
  const admin = active === "System Admin";
  const reporter = ["Finance Staff", "Auditor", ...authorities].includes(active);
  const requests = useQuery({ queryKey: ["iaa", active, "requests"], enabled: !!active && !admin,
    queryFn: () => get<{ results: RequestRow[] }>("requests", active) });
  const detail = useQuery({ queryKey: ["iaa", active, "request", selected], enabled: !!selected && !admin,
    queryFn: () => get<RequestRow>(`requests/${selected}`, active) });
  const anomalies = useQuery({ queryKey: ["iaa", active, "anomalies"], enabled: !!active && !admin,
    queryFn: () => get<{ results: Row[] }>("anomalies", active) });
  const observations = useQuery({ queryKey: ["iaa", active, "observations"], enabled: !!active && !admin,
    queryFn: () => get<{ results: Row[] }>("observations", active) });
  const messages = useQuery({ queryKey: ["iaa", active, "notifications"], enabled: !!active && !admin,
    queryFn: () => get<{ results: Row[] }>("notifications", active) });
  const reports = useQuery({ queryKey: ["iaa", active, "reports"], enabled: reporter,
    queryFn: () => get<{ requests: number; amount: string; statuses: Record<string, number>;
      average_turnaround_seconds: number | null; average_approval_turnaround_seconds: number | null;
      anomalies: { status: string; count: number }[];
      observations: { status: string; count: number }[] }>("reports", active) });
  const invalidate = () => qc.invalidateQueries({ queryKey: ["iaa"] });
  const switching = useMutation({ mutationFn: (value: string) => post("session", value, { role: value }),
    onSuccess: (_, value) => {
      setRole(value); sessionStorage.setItem(`iaa-role:${userId}`, value);
      setSelected(null); setEditor(null); setPending(null); setTab("requests");
      qc.removeQueries({ queryKey: ["iaa"] });
    } });
  const action = useMutation({ mutationFn: (p: Pending) => post(p.path, active, {
    ...p.body, ...(p.field ? { [p.field]: remarks } : {}),
    ...(p.evidence ? { evidence: evidenceLinks(evidence) } : {}),
  }), onSuccess: () => { setPending(null); invalidate(); } });
  const saving = useMutation({ mutationFn: async (form: Record<string, string>) => {
    const { id, documents, ...rest } = form;
    const data = { ...rest, documents: evidenceLinks(documents ?? ""), amount: rest.amount || null,
      trip_start: rest.trip_start || null, trip_end: rest.trip_end || null };
    if (id) return http.patch(`/iaa/requests/${id}`, data, { headers: headers(active) });
    return post("requests", active, data);
  }, onSuccess: () => { setEditor(null); invalidate(); } });
  const downloading = useMutation({ mutationFn: async () => {
    try {
      const response = await http.get("/iaa/reports?export=csv", { headers: headers(active), responseType: "blob" });
      saveBlob(response.data, "iaa-report.csv");
    } catch (error) { throw await readBlobError(error); }
  } });
  function open(p: Pending) { action.reset(); setRemarks(""); setEvidence(""); setPending(p); }
  function edit(row?: RequestRow) {
    saving.reset();
    setEditor(row ? { id: String(row.id), kind: row.kind, request_type: row.request_type,
      department: row.department, description: row.description, amount: row.amount ?? "",
      documents: row.documents.join("\n"), trip_start: String(row.trip_start ?? ""), trip_end: String(row.trip_end ?? "") }
      : { kind: "expense", request_type: "", department: "", description: "", amount: "", documents: "", trip_start: "", trip_end: "" });
  }
  function requestAction(row: RequestRow, choice: string) {
    if (choice === "edit") { edit(row); return; }
    const target = ["approve", "reject"].includes(choice) ? "decide" : choice === "reject_ta" ? "validate" : choice;
    const body = choice === "approve" ? { approve: true } : choice === "reject" ? { approve: false }
      : choice === "reject_ta" ? { compliant: false } : choice === "anomaly" ? { category: "policy" } : {};
    const field = choice === "submit" ? undefined : choice === "record" ? "reference"
      : ["anomaly", "observation"].includes(choice) ? "description" : choice === "respond" ? "response" : "remarks";
    open({ path: `requests/${row.id}/${target}`, title: label(choice), body, field, evidence: choice === "respond" });
  }
  return <Container size="xl" py="md"><Stack gap="lg">
    <Group justify="space-between"><div><Text size="xs" c="dimmed" tt="uppercase">Fusion · Finance governance</Text>
      <Title order={1}>Institute Accounts and Audits</Title>
      <Text c="dimmed">Financial requests, approvals, and accountable follow-up.</Text></div>
      <Select label="Active IAA role" placeholder="Select a role" value={active || null} data={assigned}
        disabled={switching.isPending} onChange={v => v && switching.mutate(v)} /></Group>
    {session.isPending && <Loader />}
    {(session.error || switching.error) && <Alert color="red">{errorMessage(session.error ?? switching.error)}</Alert>}
    {!session.isPending && !assigned.length && <Alert title="IAA access needs configuration">
      Ask your IAA administrator to assign your role and department scope.</Alert>}
    {!!assigned.length && !active && <Alert>Select the role you want to use. Permissions and historical actions are kept separate for each role.</Alert>}
    {!!active && (admin ? <ConfigPanel role={active} /> : <Tabs value={tab} onChange={setTab}>
      <Tabs.List><Tabs.Tab value="requests">{active === "Basic User" ? "My requests" : "Financial records"}</Tabs.Tab>
        <Tabs.Tab value="tasks">Pending actions</Tabs.Tab>
        <Tabs.Tab value="anomalies">Anomalies</Tabs.Tab><Tabs.Tab value="observations">Audit observations</Tabs.Tab>
        <Tabs.Tab value="notifications">Notifications</Tabs.Tab>{reporter && <Tabs.Tab value="reports">Reports</Tabs.Tab>}</Tabs.List>
      <Tabs.Panel value="requests" pt="md"><Stack>
        <Group justify="space-between"><Text size="sm" c="dimmed">Your authorized records, newest first (up to 200).</Text>
          {active === "Basic User" && <Button onClick={() => edit()}>New expense / TA claim</Button>}</Group>
        {requests.isPending && <Loader />}{requests.error && <Alert color="red">{errorMessage(requests.error)}</Alert>}
        {!requests.isPending && !requests.error && !requests.data?.results.length && <Paper p="xl" withBorder><Title order={3}>No requests yet</Title>
          <Text c="dimmed">Requests in your active role and department scope will appear here.</Text></Paper>}
        {!!requests.data?.results.length && <Table.ScrollContainer minWidth={780}><Table highlightOnHover>
          <Table.Thead><Table.Tr>{["Record", "Department", "Description", "Amount", "Status", ""].map(x => <Table.Th key={x}>{x}</Table.Th>)}</Table.Tr></Table.Thead>
          <Table.Tbody>{requests.data.results.map(row => <Table.Tr key={row.id}>
            <Table.Td>#{row.id} · {row.kind === "ta" ? "TA" : "Expense"}</Table.Td><Table.Td>{row.department || "—"}</Table.Td>
            <Table.Td><Text lineClamp={2} size="sm">{row.description || "Incomplete draft"}</Text></Table.Td>
            <Table.Td>{currency(row.amount)}</Table.Td><Table.Td><Status value={row.status} /></Table.Td>
            <Table.Td><Button variant="light" size="xs" onClick={() => setSelected(row.id)}>Open record</Button></Table.Td>
          </Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer>}
      </Stack></Tabs.Panel>
      <Tabs.Panel value="tasks" pt="md"><Stack>
        <Title order={3}>Actions for your active role</Title>
        {requests.error && <Alert color="red">{errorMessage(requests.error)}</Alert>}
        {requests.isPending && <Loader />}
        {requests.data?.results.filter(row => requestActions(row, active, userId)
          .some(a => !["edit", "anomaly", "observation"].includes(a))).map(row => <Paper key={row.id} p="md" withBorder>
          <Group justify="space-between"><div><Text fw={600}>Record #{row.id} · {currency(row.amount)}</Text>
            <Status value={row.status} />{row.assigned_at ? <Text size="xs" c="dimmed">Assigned {when(row.assigned_at)}</Text> : null}</div>
            <Button variant="light" onClick={() => setSelected(row.id)}>Review action</Button></Group>
        </Paper>)}
        {!requests.isPending && !requests.error && !requests.data?.results.some(row => requestActions(row, active, userId)
          .some(a => !["edit", "anomaly", "observation"].includes(a))) && <Text c="dimmed">No financial request actions are waiting for this role.</Text>}
        <Text size="sm">Assigned anomaly resolutions and audit responses are listed in the Anomalies and Audit observations tabs.</Text>
      </Stack></Tabs.Panel>
      <Tabs.Panel value="anomalies" pt="md"><Stack>
        {anomalies.isPending && <Loader />}{anomalies.error && <Alert color="red">{errorMessage(anomalies.error)}</Alert>}
        {!anomalies.isPending && !anomalies.error && !anomalies.data?.results.length && <Text c="dimmed">No anomalies in your scope.</Text>}
        {anomalies.data?.results.map(row => <Paper key={row.id} withBorder p="md"><Stack gap="sm">
          <Group justify="space-between"><Title order={4}>Anomaly #{row.id} · {label(String(row.category))}</Title><Status value={String(row.status)} /></Group>
          <Text>{String(row.description)}</Text><Text size="sm">Record #{String(row.request)} · Resolver: {String(row.resolver_role)} #{String(row.resolver_id)}</Text>
          {row.resolution ? <Text size="sm">Latest resolution: {String(row.resolution)}</Text> : null}
          {row.resolver_id === userId && row.resolver_role === active && row.status !== "resolved" && <Group>
            <Button onClick={() => open({ path: `anomalies/${row.id}/resolve`, title: "Resolve anomaly", field: "remarks", body: { escalate: false } })}>Resolve</Button>
            {row.status === "open" && <Button variant="light" onClick={() => open({ path: `anomalies/${row.id}/resolve`, title: "Escalate anomaly", field: "remarks", body: { escalate: true } })}>Escalate</Button>}
          </Group>}
        </Stack></Paper>)}
      </Stack></Tabs.Panel>
      <Tabs.Panel value="observations" pt="md"><Stack>
        {observations.isPending && <Loader />}{observations.error && <Alert color="red">{errorMessage(observations.error)}</Alert>}
        {!observations.isPending && !observations.error && !observations.data?.results.length && <Text c="dimmed">No audit observations in your scope.</Text>}
        {observations.data?.results.map(row => <Paper key={row.id} withBorder p="md"><Stack gap="sm">
          <Group justify="space-between"><Title order={4}>Observation #{row.id}</Title><Status value={String(row.status)} /></Group>
          <Text>{String(row.description)}</Text><Text size="sm">Record #{String(row.request)}</Text>
          {row.response ? <Text>Corrective action: {String(row.response)}</Text> : null}<Links values={row.evidence} />
          {row.verification ? <Text>Verification: {String(row.verification)}</Text> : null}
          {row.status === "open" && active === "Basic User" && row.respondent_id === userId && <Button onClick={() => open({
            path: `observations/${row.id}/respond`, title: "Submit corrective action", field: "response", evidence: true, body: {} })}>Respond with evidence</Button>}
          {row.status === "responded" && active === "Auditor" && row.auditor_id === userId && <Group>
            <Button onClick={() => open({ path: `observations/${row.id}/review`, title: "Verify and close", field: "verification", body: { satisfactory: true } })}>Verify and close</Button>
            <Button variant="light" onClick={() => open({ path: `observations/${row.id}/review`, title: "Return for rework", field: "verification", body: { satisfactory: false } })}>Return for rework</Button>
          </Group>}
        </Stack></Paper>)}
      </Stack></Tabs.Panel>
      <Tabs.Panel value="notifications" pt="md"><Stack>
        {messages.isPending && <Loader />}{messages.error && <Alert color="red">{errorMessage(messages.error)}</Alert>}
        {!messages.isPending && !messages.error && !messages.data?.results.length && <Text c="dimmed">No notifications for this role.</Text>}
        {messages.data?.results.map(row => <Paper key={row.id} p="md" withBorder><Text>{String(row.message)}</Text><Text c="dimmed" size="xs">{when(row.at)}</Text></Paper>)}
      </Stack></Tabs.Panel>
      {reporter && <Tabs.Panel value="reports" pt="md"><Stack>
        {reports.isPending && <Loader />}{reports.error && <Alert color="red">{errorMessage(reports.error)}</Alert>}
        {reports.data && <><SimpleGrid cols={{ base: 1, sm: 3 }}>
          <Paper p="lg" withBorder><Text c="dimmed">Requests in scope</Text><Title>{reports.data.requests}</Title></Paper>
          <Paper p="lg" withBorder><Text c="dimmed">Total requested</Text><Title order={2}>{currency(reports.data.amount)}</Title></Paper>
          <Paper p="lg" withBorder><Text c="dimmed">Average approval turnaround</Text><Title order={2}>{reports.data.average_approval_turnaround_seconds == null ? "—" : `${(reports.data.average_approval_turnaround_seconds / 3600).toFixed(1)} hours`}</Title></Paper>
        </SimpleGrid><Group>{Object.entries(reports.data.statuses).map(([status, count]) => <Badge key={status} size="lg" variant="light">{label(status)}: {count}</Badge>)}</Group>
        <Title order={4}>Anomalies</Title><Group>{reports.data.anomalies.map(r => <Badge key={r.status}>{label(r.status)}: {r.count}</Badge>)}</Group>
        <Title order={4}>Audit observations</Title><Group>{reports.data.observations.map(r => <Badge key={r.status}>{label(r.status)}: {r.count}</Badge>)}</Group></>}
        <Button variant="light" loading={downloading.isPending} onClick={() => downloading.mutate()}>Export scoped report (CSV)</Button>
        {downloading.error && <Alert color="red">{errorMessage(downloading.error)}</Alert>}
      </Stack></Tabs.Panel>}
    </Tabs>)}
  </Stack>
  <Modal opened={selected !== null} onClose={() => setSelected(null)} title={`Financial record #${selected}`} size="xl"><Stack>
    {detail.isPending && <Loader />}{detail.error && <Alert color="red">{errorMessage(detail.error)}</Alert>}
    {detail.data && <><Group><Status value={detail.data.status} /><Text fw={600}>{currency(detail.data.amount)}</Text></Group>
      <Text>{detail.data.description || "Incomplete draft"}</Text><Text size="sm">{detail.data.department} · {detail.data.request_type}</Text>
      <Links values={detail.data.documents} />
      {detail.data.recovery_note ? <Alert color="yellow">{String(detail.data.recovery_note)}</Alert> : null}
      {detail.data.status === "draft" && Array.isArray(detail.data.missing_fields) && !!detail.data.missing_fields.length && <Alert>
        Complete before submitting: {detail.data.missing_fields.map(String).join(", ")}</Alert>}
      {detail.data.assignee_id && <Text size="sm">Assigned to {detail.data.assignee_role} #{detail.data.assignee_id}</Text>}
      <Group>{requestActions(detail.data, active, userId).map(choice => <Button key={choice} size="sm" variant="light"
        color={choice.startsWith("reject") ? "red" : "blue"} onClick={() => requestAction(detail.data!, choice)}>{label(choice)}</Button>)}</Group>
      <Title order={4}>Clarifications</Title>{!detail.data.clarifications?.length && <Text c="dimmed">None.</Text>}
      {detail.data.clarifications?.map(row => <Paper key={row.id} withBorder p="sm"><Text fw={600}>{String(row.query)}</Text>
        <Text>{row.response ? String(row.response) : "Awaiting response"}</Text><Links values={row.evidence} /></Paper>)}
      <Title order={4}>Action history</Title>{detail.data.history?.map(row => <Paper key={row.id} withBorder p="sm"><Text fw={600}>{label(String(row.action))}</Text>
        <Text size="sm">{String(row.active_role)} · {row.actor_id ? `User ${row.actor_id}` : "System"} · {when(row.at)}</Text>
        <Text size="sm">{row.from_status ? `${label(String(row.from_status))} → ` : ""}{label(String(row.to_status ?? ""))}</Text>
        {row.details && typeof row.details === "object" ? Object.entries(row.details).map(([key, value]) => <Text key={key} size="sm">{label(key)}: {Array.isArray(value) ? value.join(", ") : String(value)}</Text>) : null}
      </Paper>)}</>}
  </Stack></Modal>
  <Modal opened={editor !== null} onClose={() => setEditor(null)} title={editor?.id ? "Edit expense draft" : "New expense or TA claim"} size="lg">
    <form onSubmit={e => { e.preventDefault(); if (editor) saving.mutate(editor); }}><Stack>
      <Select label="Request kind" value={editor?.kind ?? "expense"} disabled={!!editor?.id}
        data={[{ value: "expense", label: "Expense / voucher draft" }, { value: "ta", label: "Travel allowance claim" }]}
        onChange={v => setEditor(f => ({ ...f, kind: v ?? "expense" }))} />
      <Text size="sm" c="dimmed">Expense drafts may be incomplete. TA claims are validated and submitted immediately.</Text>
      {["request_type", "department", "amount"].map(field => <TextInput key={field} label={label(field)} required={editor?.kind === "ta"}
        inputMode={field === "amount" ? "decimal" : undefined} value={editor?.[field] ?? ""}
        onChange={e => { const v = e.currentTarget.value; setEditor(f => ({ ...f, [field]: v })); }} />)}
      <Textarea label="Description / trip purpose" required={editor?.kind === "ta"} value={editor?.description ?? ""}
        onChange={e => { const v = e.currentTarget.value; setEditor(f => ({ ...f, description: v })); }} />
      {editor?.kind === "ta" && <Group grow>{["trip_start", "trip_end"].map(field => <TextInput type="date" label={label(field)} key={field} required
        value={editor[field] ?? ""} onChange={e => { const v = e.currentTarget.value; setEditor(f => ({ ...f, [field]: v })); }} />)}</Group>}
      <Textarea label="Supporting document links" description="One HTTPS evidence link per line. Use access-controlled institute storage."
        value={editor?.documents ?? ""} onChange={e => { const v = e.currentTarget.value; setEditor(f => ({ ...f, documents: v })); }} />
      {saving.error && <Alert color="red">{errorMessage(saving.error)}</Alert>}
      <Button type="submit" loading={saving.isPending}>{editor?.kind === "ta" ? "Submit TA claim" : "Save draft"}</Button>
    </Stack></form>
  </Modal>
  <Modal opened={pending !== null} onClose={() => setPending(null)} title={pending?.title}>
    <form onSubmit={e => { e.preventDefault(); if (pending) action.mutate(pending); }}><Stack>
      {pending?.field && <Textarea label={label(pending.field)} required value={remarks} onChange={e => setRemarks(e.currentTarget.value)} />}
      {pending?.evidence && <Textarea label="Supporting evidence links (HTTPS, one per line)" required={pending.path.startsWith("observations/")}
        value={evidence} onChange={e => setEvidence(e.currentTarget.value)} />}
      {pending?.path.endsWith("/record") && <Alert>This records internal processing completion. No bank transfer is initiated.</Alert>}
      {pending?.path.endsWith("/validate") && <Alert>Confirm documentary and policy review. Department budget availability is checked automatically.</Alert>}
      {action.error && <Alert color="red">{errorMessage(action.error)}</Alert>}
      <Button type="submit" loading={action.isPending}>Confirm {pending?.title.toLowerCase()}</Button>
    </Stack></form>
  </Modal></Container>;
}
