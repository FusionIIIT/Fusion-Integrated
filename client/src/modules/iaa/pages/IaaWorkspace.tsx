import {
  Alert, Anchor, Badge, Button, Card, FileInput, Group, NumberInput,
  Select, SimpleGrid, Stack, Text, TextInput, Textarea, Title,
} from "@mantine/core";
import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation } from "react-router-dom";

import { errorMessage, http } from "../../../lib/http";
import { saveBlob } from "../../../lib/download";
import { activeRole, getActiveRoles, list, setActiveRole,
         type IaaNotification, type IaaRecord } from "../api";

const pages = [
  ["Expense / Voucher Requests", "/iaa/requests"],
  ["Finance Queue", "/iaa/finance"],
  ["Approvals", "/iaa/approvals"],
  ["Travel Allowance", "/iaa/ta"],
  ["Anomalies", "/iaa/anomalies"],
  ["Audit Observations", "/iaa/audit-observations"],
  ["Reports", "/iaa/reports"],
  ["Notifications", "/iaa/notifications"],
  ["Configuration", "/iaa/configuration"],
] as const;

export default function IaaWorkspace() {
  const location = useLocation();
  const path = location.pathname;
  const [role, setRole] = useState(activeRole());
  const [roles, setRoles] = useState<string[]>([]);
  const [rows, setRows] = useState<IaaRecord[]>([]);
  const [notifications, setNotifications] = useState<IaaNotification[]>([]);
  const [configuration, setConfiguration] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    getActiveRoles().then((data) => {
      setRoles(data.roles);
      if (role && data.roles.includes(role)) return;
      if (data.roles.length === 1 && data.roles[0]) {
        void chooseRole(data.roles[0]);
      }
    }).catch((e: unknown) => setError(errorMessage(e)));
  // Role selection is deliberately local to this IAA context and is sent on
  // every IAA API call; IAM remains responsible for identity and role claims.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!role) return;
    setError("");
    if (path.endsWith("/notifications")) {
      list<IaaNotification>("/iaa/notifications").then(setNotifications)
        .catch((e: unknown) => setError(errorMessage(e)));
      return;
    }
    if (path.endsWith("/configuration")) {
      http.get("/iaa/configuration").then((res) => setConfiguration(res.data))
        .catch((e: unknown) => setError(errorMessage(e)));
      return;
    }
    const endpoint = path.endsWith("/ta") ? "/iaa/ta-claims"
      : path.endsWith("/anomalies") ? "/iaa/anomalies"
      : path.endsWith("/audit-observations") ? "/iaa/audit-observations"
      : "/iaa/requests";
    list<IaaRecord>(endpoint).then(setRows)
      .catch((e: unknown) => setError(errorMessage(e)));
  }, [path, role, refresh]);

  async function chooseRole(next: string) {
    setError("");
    try {
      await setActiveRole(next);
      setRole(next);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  async function run(action: () => Promise<unknown>) {
    setBusy(true); setError("");
    try { await action(); setRefresh((n) => n + 1); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }

  const heading = pages.find(([, to]) => path === to)?.[0] ?? "Institute Accounts and Audits";
  const section = path.endsWith("/ta") ? "ta"
    : path.endsWith("/anomalies") ? "anomalies"
    : path.endsWith("/audit-observations") ? "audit"
    : path.endsWith("/reports") ? "reports"
    : path.endsWith("/notifications") ? "notifications"
    : path.endsWith("/configuration") ? "configuration"
    : path.endsWith("/approvals") ? "approvals"
    : path.endsWith("/finance") ? "finance" : "requests";

  return (
    <Stack gap="md" p="md">
      <Group justify="space-between" align="end">
        <div><Title order={2}>{heading}</Title>
          <Text c="dimmed" size="sm">Internal financial governance and audit history</Text></div>
        <Select label="Active IAA role" placeholder="Select a role" value={role || null}
          data={roles} onChange={(value) => value && void chooseRole(value)} w={220} />
      </Group>
      <Group gap="xs" wrap="wrap">
        {pages.map(([label, to]) => <Anchor component={Link} to={to} key={to} size="sm">{label}</Anchor>)}
      </Group>
      {error && <Alert color="red" title="Could not complete this action">{error}</Alert>}
      {!role ? <Alert title="Select an active IAA role">Choose one of your assigned roles to continue.</Alert>
        : section === "requests" || section === "finance" || section === "approvals"
          ? <RequestWorkspace section={section} rows={rows} run={run} busy={busy} />
        : section === "ta" ? <TaWorkspace rows={rows} run={run} busy={busy} />
        : section === "anomalies" ? <AnomalyWorkspace rows={rows} run={run} busy={busy} />
        : section === "audit" ? <AuditWorkspace rows={rows} run={run} busy={busy} />
        : section === "notifications" ? <NotificationWorkspace rows={notifications} run={run} />
        : section === "configuration" ? <ConfigurationWorkspace data={configuration} />
        : <ReportsWorkspace />}
    </Stack>
  );
}

type Runner = (action: () => Promise<unknown>) => Promise<void>;

function RequestWorkspace({ section, rows, run, busy }: {
  section: string; rows: IaaRecord[]; run: Runner; busy: boolean;
}) {
  const myForm = section === "requests";
  const role = activeRole();
  return <Stack>
    {myForm && role === "Basic User" && <RequestForm run={run} busy={busy} />}
    <RecordList rows={rows} requestActions={run} busy={busy} role={role}
      type="request" finance={section === "finance"} approvals={section === "approvals"} />
  </Stack>;
}

function RequestForm({ run, busy }: { run: Runner; busy: boolean }) {
  const [requestId, setRequestId] = useState<number | null>(null);
  const [requestType, setType] = useState(""); const [department, setDepartment] = useState("");
  const [amount, setAmount] = useState<number | string>(""); const [description, setDescription] = useState("");
  const [evidence, setEvidence] = useState<File | null>(null);
  async function save(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const saved = await http.post("/iaa/requests", { request_type: requestType,
        department, amount: amount === "" ? null : amount, description,
        supporting_information: {} });
      setRequestId(saved.data.id);
      if (evidence) {
        const form = new FormData(); form.append("record_type", "request");
        form.append("record_id", String(saved.data.id)); form.append("purpose", "supporting_document");
        form.append("file", evidence); await http.post("/iaa/evidence", form);
      }
    });
  }
  return <Card withBorder><form onSubmit={(e) => void save(e)}><Stack>
    <Title order={4}>Create an expense or voucher request</Title>
    <SimpleGrid cols={{ base: 1, md: 2 }}>
      <TextInput label="Request type" required value={requestType} onChange={(e) => setType(e.currentTarget.value)} />
      <TextInput label="Department" required value={department} onChange={(e) => setDepartment(e.currentTarget.value)} />
      <NumberInput label="Amount" min={0} required value={amount} onChange={setAmount} />
      <FileInput label="Supporting document" value={evidence} onChange={setEvidence} />
    </SimpleGrid>
    <Textarea label="Description" required minRows={3} value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
    <Group><Button type="submit" loading={busy}>Save draft</Button>
      {requestId && <Button variant="light" loading={busy} onClick={() => void run(() => http.post(`/iaa/requests/${requestId}/submit`))}>Submit request</Button>}
    </Group>
  </Stack></form></Card>;
}

function RecordList({ rows, requestActions, busy, role, type, finance, approvals }: {
  rows: IaaRecord[]; requestActions: Runner; busy: boolean; role: string;
  type: "request" | "ta_claim"; finance?: boolean; approvals?: boolean;
}) {
  if (!rows.length) return <Card withBorder><Text c="dimmed">No records are visible for this role.</Text></Card>;
  return <Stack>{rows.map((row) => <Card withBorder key={row.id}>
    <Group justify="space-between"><div><Text fw={600}>{type === "request" ? row.request_type : row.purpose} #{row.id}</Text>
      <Text size="sm" c="dimmed">{row.department} · {type === "request" ? row.amount : row.claimed_amount}</Text></div>
      <Badge>{row.status}</Badge></Group>
    <Text mt="sm">{row.description ?? row.purpose}</Text>
    <Group mt="md">
      {finance && role === "Finance Staff" && ["Submitted", "Query Responded"].includes(row.status) && <>
        <Button size="xs" loading={busy} onClick={() => void requestActions(() => http.post(`/iaa/${type === "request" ? "requests" : "ta-claims"}/${row.id}/${type === "request" ? "review" : "verify"}`, { action: type === "request" ? "validate" : "verify", policy_passed: true, remarks: "Finance validation completed." }))}>Validate</Button>
        <Button size="xs" variant="light" loading={busy} onClick={() => void requestActions(() => http.post(`/iaa/${type === "request" ? "requests" : "ta-claims"}/${row.id}/${type === "request" ? "review" : "verify"}`, { action: "clarification", remarks: "Please provide the required clarification or evidence." }))}>Request clarification</Button>
      </>}
      {approvals && ["HoD", "Dean", "Director"].includes(role) &&
        ["Approval Pending", "Escalated", "Finance Validated"].includes(row.status) && <>
        <Button size="xs" loading={busy} onClick={() => void requestActions(() => http.post(`/iaa/${type === "request" ? "requests" : "ta-claims"}/${row.id}/decision`, { decision: "Approved", remarks: "Approved." }))}>Approve</Button>
        <Button size="xs" color="red" loading={busy} onClick={() => void requestActions(() => http.post(`/iaa/${type === "request" ? "requests" : "ta-claims"}/${row.id}/decision`, { decision: "Rejected", remarks: "Rejected." }))}>Reject</Button>
      </>}
      {finance && role === "Finance Staff" && row.status === "Approved" && <Button size="xs" loading={busy} onClick={() => void requestActions(() => http.post(`/iaa/${type === "request" ? "requests" : "ta-claims"}/${row.id}/record`, { processing_details: "Internal processing recorded." }))}>Record internal processing</Button>}
      {type === "request" && role === "Basic User" && row.status === "Draft" && <Button size="xs" loading={busy} onClick={() => void requestActions(() => http.post(`/iaa/requests/${row.id}/submit`))}>Submit</Button>}
      <HistoryButton recordType={type} recordId={row.id} />
    </Group>
    {role === "Basic User" && row.status === "Query Raised" &&
      <ClarificationForm id={row.id} type={type} run={requestActions} busy={busy} />}
  </Card>)}</Stack>;
}

function ClarificationForm({ id, type, run, busy }: {
  id: number; type: "request" | "ta_claim"; run: Runner; busy: boolean;
}) {
  const [response, setResponse] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const url = type === "request" ? "requests" : "ta-claims";
  return <Stack mt="sm"><Textarea label="Clarification response" value={response}
    onChange={(e) => setResponse(e.currentTarget.value)} />
    <FileInput label="Additional evidence" multiple value={files} onChange={setFiles} />
    <Button size="xs" loading={busy} onClick={() => void run(async () => {
      for (const file of files) {
        const form = new FormData(); form.append("record_type", type);
        form.append("record_id", String(id)); form.append("purpose", "clarification_evidence");
        form.append("file", file); await http.post("/iaa/evidence", form);
      }
      await http.post(`/iaa/${url}/${id}/respond`, { response });
    })}>Send response</Button>
  </Stack>;
}

function TaWorkspace({ rows, run, busy }: { rows: IaaRecord[]; run: Runner; busy: boolean }) {
  const role = activeRole();
  const [department, setDepartment] = useState(""); const [start, setStart] = useState("");
  const [end, setEnd] = useState(""); const [purpose, setPurpose] = useState("");
  const [amount, setAmount] = useState<number | string>(""); const [files, setFiles] = useState<File[]>([]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const form = new FormData(); form.append("department", department);
      form.append("trip_start", start); form.append("trip_end", end);
      form.append("purpose", purpose); form.append("claimed_amount", String(amount));
      form.append("trip_details", "{}"); files.forEach((file) => form.append("evidence", file));
      await http.post("/iaa/ta-claims", form);
      setPurpose(""); setFiles([]);
    });
  }
  return <Stack>
    {role === "Basic User" && <Card withBorder><form onSubmit={(e) => void submit(e)}><Stack>
      <Title order={4}>Submit a travel allowance claim</Title>
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <TextInput label="Department" required value={department} onChange={(e) => setDepartment(e.currentTarget.value)} />
        <NumberInput label="Claimed amount" min={0} required value={amount} onChange={setAmount} />
        <TextInput label="Trip start" type="date" required value={start} onChange={(e) => setStart(e.currentTarget.value)} />
        <TextInput label="Trip end" type="date" required value={end} onChange={(e) => setEnd(e.currentTarget.value)} />
      </SimpleGrid>
      <Textarea label="Trip purpose" required value={purpose} onChange={(e) => setPurpose(e.currentTarget.value)} />
      <FileInput label="Supporting evidence" multiple value={files} onChange={setFiles} />
      <Button type="submit" loading={busy}>Submit TA claim</Button>
    </Stack></form></Card>}
    <RecordList rows={rows} requestActions={run} busy={busy} role={role} type="ta_claim" finance approvals />
  </Stack>;
}

function AnomalyWorkspace({ rows, run, busy }: { rows: IaaRecord[]; run: Runner; busy: boolean }) {
  const role = activeRole(); const [targetId, setTargetId] = useState<number | string>("");
  const [targetType, setTargetType] = useState("request"); const [category, setCategory] = useState("");
  const [description, setDescription] = useState(""); const [resolver, setResolver] = useState("Finance Staff");
  const canFlag = ["Finance Staff", "Auditor"].includes(role);
  return <Stack>
    {canFlag && <Card withBorder><Stack><Title order={4}>Flag a material anomaly</Title>
      <Select label="Financial record" value={targetType} onChange={(v) => v && setTargetType(v)} data={["request", "ta_claim"]} />
      <NumberInput label="Record id" min={1} value={targetId} onChange={setTargetId} />
      <TextInput label="Category" value={category} onChange={(e) => setCategory(e.currentTarget.value)} />
      <Textarea label="Description" value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
      <Select label="Resolver role" value={resolver} onChange={(v) => v && setResolver(v)} data={["Finance Staff", "HoD", "Dean", "Director", "Auditor"]} />
      <Button loading={busy} onClick={() => void run(() => http.post("/iaa/anomalies", { record_type: targetType, record_id: targetId, category, description, resolver_role: resolver }))}>Flag anomaly</Button>
    </Stack></Card>}
    <SimpleGrid cols={{ base: 1, md: 2 }}>{rows.map((row) => <Card withBorder key={row.id}>
      <Group justify="space-between"><Text fw={600}>{row.description}</Text><Badge>{row.status}</Badge></Group>
      <Group mt="md"><Button size="xs" onClick={() => void run(() => http.post(`/iaa/anomalies/${row.id}/outcome`, { outcome: "Resolved", remarks: "Resolution recorded." }))}>Resolve</Button>
        <Button size="xs" variant="light" onClick={() => void run(() => http.post(`/iaa/anomalies/${row.id}/outcome`, { outcome: "Escalated", remarks: "Escalated for configured review." }))}>Escalate</Button></Group>
    </Card>)}</SimpleGrid>
  </Stack>;
}

function AuditWorkspace({ rows, run, busy }: { rows: IaaRecord[]; run: Runner; busy: boolean }) {
  const role = activeRole(); const [recordId, setRecordId] = useState<number | string>("");
  const [recordType, setRecordType] = useState("request"); const [title, setTitle] = useState("");
  const [description, setDescription] = useState(""); const [department, setDepartment] = useState("");
  return <Stack>
    {role === "Auditor" && <Card withBorder><Stack><Title order={4}>Raise an audit observation</Title>
      <Select label="Financial record" value={recordType} onChange={(v) => v && setRecordType(v)} data={["request", "ta_claim"]} />
      <NumberInput label="Record id" min={1} value={recordId} onChange={setRecordId} />
      <TextInput label="Department" value={department} onChange={(e) => setDepartment(e.currentTarget.value)} />
      <TextInput label="Title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
      <Textarea label="Observation" value={description} onChange={(e) => setDescription(e.currentTarget.value)} />
      <Button loading={busy} onClick={() => void run(() => http.post("/iaa/audit-observations", { record_type: recordType, record_id: recordId, department, title, description }))}>Raise observation</Button>
    </Stack></Card>}
    {rows.map((row) => <Card withBorder key={row.id}><Group justify="space-between"><Text fw={600}>Observation #{row.id}: {row.description}</Text><Badge>{row.status}</Badge></Group>
      {role === "Basic User" && row.status === "Open" && <Textarea mt="sm" label="Corrective action response" id={`response-${row.id}`} />}
      <Group mt="md">
        {role === "Basic User" && row.status === "Open" && <Button size="xs" onClick={() => { const value = (document.getElementById(`response-${row.id}`) as HTMLTextAreaElement | null)?.value ?? ""; void run(() => http.post(`/iaa/audit-observations/${row.id}/respond`, { response: value })); }}>Submit response</Button>}
        {role === "Auditor" && row.status === "Responded" && <>
          <Button size="xs" onClick={() => void run(() => http.post(`/iaa/audit-observations/${row.id}/verify`, { satisfactory: true, remarks: "Corrective action and evidence verified." }))}>Close after verification</Button>
          <Button size="xs" variant="light" onClick={() => void run(() => http.post(`/iaa/audit-observations/${row.id}/verify`, { satisfactory: false, remarks: "Further corrective action is required." }))}>Return for revision</Button>
        </>}
      </Group></Card>)}
  </Stack>;
}

function NotificationWorkspace({ rows, run }: { rows: IaaNotification[]; run: Runner }) {
  return <Stack>{rows.map((row) => <Card withBorder key={row.id}>
    <Group justify="space-between"><Text fw={600}>{row.title}</Text><Badge color={row.read_at ? "gray" : "blue"}>{row.read_at ? "Read" : "New"}</Badge></Group>
    <Text>{row.message}</Text><Text c="dimmed" size="xs">{new Date(row.created_at).toLocaleString()}</Text>
    {!row.read_at && <Button size="xs" variant="light" onClick={() => void run(() => http.patch(`/iaa/notifications/${row.id}`, {}))}>Mark read</Button>}
  </Card>)}</Stack>;
}

function HistoryButton({ recordType, recordId }: { recordType: string; recordId: number }) {
  const [opened, setOpened] = useState(false);
  const [rows, setRows] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState("");
  async function show() {
    setError("");
    try {
      const response = await http.get(`/iaa/history/${recordType}/${recordId}`);
      setRows(response.data.results); setOpened(true);
    } catch (e) { setError(errorMessage(e)); }
  }
  return <>
    <Button variant="subtle" size="xs" onClick={() => void show()}>History</Button>
    {opened && <Card withBorder><Stack><Group justify="space-between"><Title order={5}>Action history</Title>
      <Button size="xs" variant="subtle" onClick={() => setOpened(false)}>Close</Button></Group>
      {error && <Alert color="red">{error}</Alert>}
      {rows.map((row) => <Text size="sm" key={String(row.id)}>
        {String(row.happened_at)} · {String(row.actor_role)} · {String(row.action)} · {String(row.destination_status)} {String(row.remarks ?? "")}
      </Text>)}
    </Stack></Card>}
  </>;
}

function ReportsWorkspace() {
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const role = activeRole();
  useEffect(() => { http.get("/iaa/reports").then((res) => setReport(res.data))
    .catch((e: unknown) => setError(errorMessage(e))); }, [role]);
  async function exportReport() {
    try {
      const response = await http.get<Blob>("/iaa/reports/export.csv", { responseType: "blob" });
      saveBlob(response.data, "iaa-report.csv");
    } catch (e) { setError(errorMessage(e)); }
  }
  return <Stack>{error && <Alert color="red">{error}</Alert>}
    <Button onClick={() => void exportReport()}>Export read-only CSV</Button>
    <Card withBorder><pre style={{ whiteSpace: "pre-wrap" }}>{report ? JSON.stringify(report, null, 2) : "Loading report…"}</pre></Card>
  </Stack>;
}

function ConfigurationWorkspace({ data }: { data: Record<string, unknown> | null }) {
  const [message, setMessage] = useState(""); const [error, setError] = useState("");
  const [userId, setUserId] = useState<number | string>(""); const [assignedRole, setAssignedRole] = useState("Basic User");
  const [department, setDepartment] = useState("");
  const [yearCode, setYearCode] = useState(""); const [yearStart, setYearStart] = useState(""); const [yearEnd, setYearEnd] = useState("");
  const [yearId, setYearId] = useState<number | string>(""); const [budgetDepartment, setBudgetDepartment] = useState("");
  const [budgetAmount, setBudgetAmount] = useState<number | string>("");
  const [routeType, setRouteType] = useState(""); const [routeDepartment, setRouteDepartment] = useState("");
  const [routeMin, setRouteMin] = useState<number | string>(""); const [routeMax, setRouteMax] = useState<number | string>("");
  const [levels, setLevels] = useState("HoD"); const [escalations, setEscalations] = useState(""); const [timeout, setTimeout] = useState<number | string>("");
  const [policyCode, setPolicyCode] = useState(""); const [policyValue, setPolicyValue] = useState("{}"); const [policyFrom, setPolicyFrom] = useState("");
  const [anomalyCategory, setAnomalyCategory] = useState("Budget insufficiency"); const [resolver, setResolver] = useState("Finance Staff");

  async function save(path: string, body: unknown) {
    setError(""); setMessage("");
    try { await http.post(path, body); setMessage("Configuration saved."); }
    catch (e) { setError(errorMessage(e)); }
  }
  const roleChoices = ["Basic User", "Finance Staff", "HoD", "Dean", "Director", "Auditor", "System Admin"];
  return <Stack>
    <Alert>Thresholds, authority routes, financial years, budgets, and policy values are configured here. No institutional numeric thresholds are prefilled.</Alert>
    {error && <Alert color="red">{error}</Alert>}{message && <Alert color="green">{message}</Alert>}
    <Card withBorder><Stack><Title order={4}>Manage IAA role assignment</Title>
      <NumberInput label="IAM user id" min={1} value={userId} onChange={setUserId} />
      <Select label="IAA actor role" value={assignedRole} onChange={(v) => v && setAssignedRole(v)} data={roleChoices} />
      <TextInput label="Department scope, if applicable" value={department} onChange={(e) => setDepartment(e.currentTarget.value)} />
      <Button onClick={() => void save("/iaa/roles", { user_id: userId, role: assignedRole, department })}>Assign role</Button>
    </Stack></Card>
    <Card withBorder><Stack><Title order={4}>Financial year and department budget</Title>
      <TextInput label="Financial year code" value={yearCode} onChange={(e) => setYearCode(e.currentTarget.value)} />
      <SimpleGrid cols={2}><TextInput label="Start date" type="date" value={yearStart} onChange={(e) => setYearStart(e.currentTarget.value)} />
        <TextInput label="End date" type="date" value={yearEnd} onChange={(e) => setYearEnd(e.currentTarget.value)} /></SimpleGrid>
      <Button onClick={() => void save("/iaa/configuration/financial-years", { code: yearCode, starts_on: yearStart, ends_on: yearEnd, is_active: true })}>Save active year</Button>
      <TextInput label="Department" value={budgetDepartment} onChange={(e) => setBudgetDepartment(e.currentTarget.value)} />
      <NumberInput label="Available budget" min={0} value={budgetAmount} onChange={setBudgetAmount} />
      <NumberInput label="Financial year id" min={1} value={yearId} onChange={setYearId} />
      <Button onClick={() => void save("/iaa/configuration/budgets", { department: budgetDepartment, available_amount: budgetAmount, financial_year_id: yearId })}>Save department budget</Button>
    </Stack></Card>
    <Card withBorder><Stack><Title order={4}>Approval route and escalation</Title>
      <TextInput label="Request type (blank matches any)" value={routeType} onChange={(e) => setRouteType(e.currentTarget.value)} />
      <TextInput label="Department (blank matches any)" value={routeDepartment} onChange={(e) => setRouteDepartment(e.currentTarget.value)} />
      <SimpleGrid cols={2}><NumberInput label="Minimum amount" min={0} value={routeMin} onChange={setRouteMin} />
        <NumberInput label="Maximum amount" min={0} value={routeMax} onChange={setRouteMax} /></SimpleGrid>
      <TextInput label="Required authority levels, in order" value={levels} onChange={(e) => setLevels(e.currentTarget.value)} />
      <TextInput label="Escalation authority roles, in order" value={escalations} onChange={(e) => setEscalations(e.currentTarget.value)} />
      <NumberInput label="Approval timeout in seconds (blank means no automatic timeout)" min={1} value={timeout} onChange={setTimeout} />
      <Button onClick={() => void save("/iaa/configuration/routes", {
        request_type: routeType, department: routeDepartment,
        minimum_amount: routeMin === "" ? null : routeMin,
        maximum_amount: routeMax === "" ? null : routeMax,
        levels: levels.split(",").map((x) => x.trim()).filter(Boolean),
        escalation_roles: escalations.split(",").map((x) => x.trim()).filter(Boolean),
        timeout_seconds: timeout === "" ? null : timeout, is_active: true,
      })}>Save approval route</Button>
    </Stack></Card>
    <Card withBorder><Stack><Title order={4}>Policy parameter</Title>
      <TextInput label="Parameter code" value={policyCode} onChange={(e) => setPolicyCode(e.currentTarget.value)} />
      <Textarea label="JSON value" value={policyValue} onChange={(e) => setPolicyValue(e.currentTarget.value)} />
      <TextInput label="Effective from" type="date" value={policyFrom} onChange={(e) => setPolicyFrom(e.currentTarget.value)} />
      <Button onClick={() => { try { void save("/iaa/configuration/policies", { code: policyCode, value: JSON.parse(policyValue), effective_from: policyFrom, is_active: true }); } catch { setError("Policy value must be valid JSON."); } }}>Save policy parameter</Button>
    </Stack></Card>
    <Card withBorder><Stack><Title order={4}>Automatic budget anomaly routing</Title>
      <TextInput label="Anomaly category" value={anomalyCategory} onChange={(e) => setAnomalyCategory(e.currentTarget.value)} />
      <Select label="Designated resolver role" value={resolver} onChange={(v) => v && setResolver(v)} data={["Finance Staff", "HoD", "Dean", "Director", "Auditor"]} />
      <Button onClick={() => void save("/iaa/configuration/automatic-anomalies", { condition: "budget_insufficient", category: anomalyCategory, resolver_role: resolver, is_active: true })}>Save anomaly routing</Button>
    </Stack></Card>
    <Card withBorder><Title order={4}>Current IAA configuration</Title>
      <pre style={{ whiteSpace: "pre-wrap" }}>{data ? JSON.stringify(data, null, 2) : "Loading configuration…"}</pre></Card>
  </Stack>;
}
