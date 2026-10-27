import { useEffect, useState } from "react";
import {
  Accordion, Alert, Badge, Button, Card, Checkbox, Container, Group, Loader,
  Modal, MultiSelect, NumberInput, Select, SimpleGrid, Stack, Table, Text,
  Textarea, TextInput, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useAuth } from "../../auth/AuthProvider";
import { errorMessage, http } from "../../lib/http";
import { ErrorState } from "../../ui/components/ErrorState";
import { PageHeader } from "../../ui/components/PageHeader";
import {
  useElmQuery, useElmWrite, type Account, type Configuration, type Employee,
  type Entry, type LeaveApplication, type Notice, type Page, type Step, type Task,
} from "./api";

const categories = ["CL", "RH", "SCL", "EL", "COL", "VL"];
const label = (value: string) => value.replaceAll("_", " ");
const number = (value: string | number) => Number(value) || undefined;

function EmployeeChoice({value, onChange, label: title}: {value: string | null; onChange: (v: string | null) => void; label: string}) {
  const people = useElmQuery<Employee[]>("employees/");
  return <Select label={title} searchable clearable value={value} onChange={onChange} comboboxProps={{withinPortal:false}}
    data={(people.data ?? []).map((p) => ({value: String(p.user_id), label: `${p.display_name} (${p.user_id})`}))}
    error={people.error ? errorMessage(people.error) : undefined} />;
}

function Shell({title, children}: {title: string; children: React.ReactNode}) {
  return <Container size="xl"><PageHeader title={title} /><Stack>{children}</Stack></Container>;
}

function CursorControls({page, onChange}: {page?: Page<unknown>; onChange: (path: string) => void}) {
  return <Group>
    <Button disabled={!page?.previous} onClick={() => page?.previous && onChange(page.previous)}>Previous</Button>
    <Button disabled={!page?.next} onClick={() => page?.next && onChange(page.next)}>Next</Button>
  </Group>;
}

function ApplicationCard({app}: {app: LeaveApplication}) {
  const write = useElmWrite();
  const { session } = useAuth();
  const [action, setAction] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [end, setEnd] = useState("");
  const [substitute, setSubstitute] = useState<string | null>(null);
  const own = app.user_id === session?.user.id;
  const lifecycle = ["cancellation", "extension", "resumption"].includes(action ?? "");
  async function perform() {
    if (!action) return;
    try {
      await write.mutateAsync({
        path: `applications/${app.id}/${lifecycle ? "lifecycle" : "actions"}/`,
        data: lifecycle ? {kind: action, reason, ...(end ? {end_date: end} : {}), substitute_id: number(substitute ?? "") ?? null}
          : {action, revision: app.revision, reason, ...(substitute ? {substitute_id: number(substitute)} : {})},
      });
      setAction(null); setReason(""); setEnd(""); setSubstitute(null);
      notifications.show({title: "Saved", message: "The leave request has been updated."});
    } catch (e) { notifications.show({color: "red", title: "Could not save", message: errorMessage(e)}); }
  }
  async function download() {
    try {
      const response = await http.get(`/elm/applications/${app.id}/export/`, {responseType: "blob"});
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a"); link.href = url; link.download = `leave-${app.id}.txt`; link.click();
      URL.revokeObjectURL(url);
    } catch (e) { notifications.show({color: "red", message: errorMessage(e)}); }
  }
  return <Card withBorder padding="lg">
    <Group justify="space-between"><Title order={4}>{app.category} · Request #{app.id}</Title><Badge>{label(app.status)}</Badge></Group>
    <Text c="dimmed">{label(app.kind)} · {app.start_date} to {app.effective_end_date} · {label(app.half)} day</Text>
    <Text mt="sm">{app.reason}</Text>
    {app.station_leave && <Text size="sm">Station leave: {app.station_details}</Text>}
    <Text size="sm" c="dimmed">Days: {Object.entries(app.days_by_year).map(([y,d]) => `${y}: ${d}`).join(", ") || "No new deduction"}</Text>
    <Group mt="md">{app.allowed_actions.map((a) => <Button key={a} size="xs" variant="light" onClick={() => setAction(a)}>{label(a)}</Button>)}
      {own && app.kind === "leave" && app.status === "approved" && <>
        <Button size="xs" variant="light" onClick={() => setAction("cancellation")}>Request cancellation</Button>
        {["EL", "COL", "VL"].includes(app.category) && !app.resumption_reviewed && <>
          <Button size="xs" variant="light" onClick={() => setAction("extension")}>Request extension</Button>
          <Button size="xs" variant="light" onClick={() => setAction("resumption")}>Submit resumption</Button>
        </>}
      </>}
      {own && <Button variant="subtle" size="xs" onClick={download}>Export application</Button>}
    </Group>
    <Accordion mt="sm"><Accordion.Item value="history"><Accordion.Control>Request history</Accordion.Control>
      <Accordion.Panel><Stack gap="xs">{app.history.map((h) => <Text key={h.id} size="sm">{new Date(h.created_at).toLocaleString()} · {label(h.action)} → {label(h.to_status)}{h.reason && ` · ${h.reason}`}</Text>)}</Stack></Accordion.Panel>
    </Accordion.Item></Accordion>
    <Modal opened={Boolean(action)} onClose={() => setAction(null)} title={label(action ?? "")}>
      <Stack><Textarea label={action === "resumption" ? "Resumption details" : "Reason / comments"} value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
        {lifecycle && action !== "cancellation" && <TextInput type="date" label={action === "resumption" ? "Actual resumption date" : "Requested new end date"} value={end} onChange={(e) => setEnd(e.currentTarget.value)} />}
        {(action === "replace_substitute" || action === "extension") && <EmployeeChoice label="Substitute" value={substitute} onChange={setSubstitute} />}
        {write.error && <ErrorState error={write.error} />}<Button loading={write.isPending} onClick={perform}>Confirm {label(action ?? "action")}</Button>
      </Stack>
    </Modal>
  </Card>;
}

export function Requests() {
  const { can } = useAuth();
  const [path, setPath] = useState("applications/?scope=mine");
  const query = useElmQuery<Page<LeaveApplication>>(path, can("elm.application.self"));
  const write = useElmWrite();
  const [opened, setOpened] = useState(false);
  const [category, setCategory] = useState<string | null>("CL");
  const [start, setStart] = useState(""); const [end, setEnd] = useState("");
  const [half, setHalf] = useState<string | null>("full"); const [reason, setReason] = useState("");
  const [station, setStation] = useState(false); const [stationDetails, setStationDetails] = useState("");
  const [medical, setMedical] = useState(""); const [substitute, setSubstitute] = useState<string | null>(null);
  async function submit() {
    try {
      await write.mutateAsync({path: "applications/", data: {category, start_date: start, end_date: end, half,
        reason, station_leave: station, station_details: stationDetails, medical_reference: medical,
        substitute_id: number(substitute ?? "") ?? null}});
      setOpened(false); setReason(""); setStart(""); setEnd(""); setPath("applications/?scope=mine");
    } catch (e) { notifications.show({color: "red", message: errorMessage(e)}); }
  }
  if (!can("elm.application.self")) return <Shell title="My Leave"><Text>Switch to your employee role to manage your own leave.</Text></Shell>;
  return <Shell title="My Leave">
    <Group justify="space-between"><Text c="dimmed">Applications, decisions, and return-to-duty records</Text><Button onClick={() => setOpened(true)}>Apply for leave</Button></Group>
    {query.error && <ErrorState error={query.error} />}{query.isPending && <Loader />}
    {query.data?.results.map((a) => <ApplicationCard key={a.id} app={a} />)}
    {query.data && !query.data.results.length && <Text c="dimmed">No leave applications yet.</Text>}
    <CursorControls page={query.data} onChange={setPath} />
    <Modal opened={opened} onClose={() => setOpened(false)} title="Apply for leave"><Stack>
      <Select label="Leave category" data={categories} value={category} onChange={setCategory} />
      <Group grow><TextInput label="Start date" type="date" value={start} onChange={(e) => setStart(e.currentTarget.value)} /><TextInput label="End date" type="date" value={end} onChange={(e) => setEnd(e.currentTarget.value)} /></Group>
      <Select label="Day portion" data={[{value:"full",label:"Full day"},{value:"first",label:"First half (CL)"},{value:"second",label:"Second half (CL)"}]} value={half} onChange={setHalf} />
      <Textarea label="Purpose / reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
      <Checkbox label="I will be outside Jabalpur (Station Leave)" checked={station} onChange={(e) => setStation(e.currentTarget.checked)} />
      {station && <Textarea label="Station leave details" value={stationDetails} onChange={(e) => setStationDetails(e.currentTarget.value)} />}
      {category === "COL" && <TextInput label="Medical evidence reference" value={medical} onChange={(e) => setMedical(e.currentTarget.value)} />}
      <EmployeeChoice label="Substitute, when required" value={substitute} onChange={setSubstitute} />
      {write.error && <ErrorState error={write.error} />}<Button loading={write.isPending} disabled={!start || !end || !reason} onClick={submit}>Submit application</Button>
    </Stack></Modal>
  </Shell>;
}

export function Tasks() {
  const {can} = useAuth();
  const [path, setPath] = useState("tasks/");
  const tasks = useElmQuery<Page<Task>>(path, can("elm.task.act"));
  const [selected, setSelected] = useState<number | null>(null);
  const application = useElmQuery<LeaveApplication>(`applications/${selected}/`, selected !== null);
  return <Shell title="Assigned Leave Tasks">
    {tasks.error && <ErrorState error={tasks.error} />}{tasks.isPending && <Loader />}
    {tasks.data?.results.map((t) => <Card withBorder key={t.id}><Group justify="space-between"><Text>Request #{t.application_id} · {label(t.stage)} · {t.role}</Text><Button variant="light" onClick={() => setSelected(t.application_id)}>Review request</Button></Group></Card>)}
    {tasks.data && !tasks.data.results.length && <Text c="dimmed">No pending tasks in your active role.</Text>}
    <CursorControls page={tasks.data} onChange={setPath} />
    {application.error && selected !== null && <ErrorState error={application.error} />}
    {application.data && <ApplicationCard app={application.data} />}
  </Shell>;
}

export function Balances() {
  const accounts = useElmQuery<Account[]>("accounts/");
  const [path, setPath] = useState("ledger/");
  const ledger = useElmQuery<Page<Entry>>(path);
  return <Shell title="Balances and History">
    {accounts.error && <ErrorState error={accounts.error} />}{accounts.isPending && <Loader />}
    {accounts.data?.map((a) => <Card withBorder key={a.year}><Title order={4}>{a.year}</Title><SimpleGrid cols={{base:2,sm:6}} mt="md">{categories.map((c) => <Stack key={c} gap={2}><Text size="sm" c="dimmed">{c}</Text><Text size="xl" fw={700}>{a[c.toLowerCase() as keyof Account]} days</Text></Stack>)}</SimpleGrid></Card>)}
    <Card withBorder><Title order={4}>Account transactions</Title>{ledger.error && <ErrorState error={ledger.error} />}
      <Table><Table.Thead><Table.Tr><Table.Th>Year</Table.Th><Table.Th>Category</Table.Th><Table.Th>Days</Table.Th><Table.Th>Operation</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{ledger.data?.results.map((e) => <Table.Tr key={e.id}><Table.Td>{e.year}</Table.Td><Table.Td>{e.category}</Table.Td><Table.Td>{e.delta}</Table.Td><Table.Td>{label(e.operation)}</Table.Td></Table.Tr>)}</Table.Tbody></Table>
      {ledger.data && !ledger.data.results.length && <Text c="dimmed">No balance adjustments yet.</Text>}
    </Card>
    <CursorControls page={ledger.data} onChange={setPath} />
  </Shell>;
}

export function LeaveNotifications() {
  const [path, setPath] = useState("notifications/");
  const query = useElmQuery<Page<Notice>>(path); const write = useElmWrite();
  return <Shell title="Leave Notifications">{query.error && <ErrorState error={query.error} />}{query.isPending && <Loader />}
    {query.data?.results.map((n) => <Card withBorder key={n.id}><Group justify="space-between"><Text>{n.message}</Text>{!n.read && <Button variant="light" size="xs" loading={write.isPending} onClick={() => write.mutate({path:`notifications/${n.id}/read/`,data:{}})}>Mark read</Button>}</Group></Card>)}
    {write.error && <ErrorState error={write.error} />}{query.data && !query.data.results.length && <Text c="dimmed">No notifications yet.</Text>}
    <CursorControls page={query.data} onChange={setPath} />
  </Shell>;
}

export function LeaveConfiguration() {
  const {can} = useAuth();
  const query = useElmQuery<Configuration>("configuration/", can("elm.configuration.manage"));
  const write = useElmWrite();
  const [reminder, setReminder] = useState<string | number>(24); const [escalation, setEscalation] = useState<string | number>(48);
  const [weekdays, setWeekdays] = useState<string[]>(["5","6"]); const [medical, setMedical] = useState(false);
  const [employee, setEmployee] = useState<string | null>(null); const [unit, setUnit] = useState(""); const [designation, setDesignation] = useState("");
  const [eligible, setEligible] = useState<string[]>(["CL","RH","SCL","EL","COL"]); const [coverage, setCoverage] = useState(false);
  const [head, setHead] = useState<string | null>(null); const [final, setFinal] = useState<string | null>(null); const [finalRole, setFinalRole] = useState<string | null>("Registrar");
  const [establishment, setEstablishment] = useState<string | null>(null);
  const [routingChanged, setRoutingChanged] = useState(false);
  const [year, setYear] = useState<string | number>(new Date().getFullYear()); const [holidays, setHolidays] = useState(""); const [rh, setRh] = useState(""); const [publish, setPublish] = useState(false);
  useEffect(() => {
    const policy = query.data?.policy;
    if (policy) {
      setReminder(policy.reminder_hours); setEscalation(policy.escalation_hours);
      setWeekdays(policy.non_working_weekdays.map(String)); setMedical(policy.require_col_evidence);
    }
  }, [query.data?.policy]);
  useEffect(() => {
    setRoutingChanged(false);
    const existing = query.data?.employees.find((row) => row.user_id === Number(employee));
    if (!existing) {
      setUnit(""); setDesignation(""); setCoverage(false); setEligible(["CL","RH","SCL","EL","COL"]);
      setHead(null); setFinal(null); setFinalRole("Registrar"); setEstablishment(null);
      return;
    }
    setUnit(existing.unit); setDesignation(existing.designation);
    setEligible(existing.eligible_categories); setCoverage(existing.coverage_required);
    const route = existing.routes.EL ?? existing.routes.SCL ?? Object.values(existing.routes)[0] ?? [];
    const unitHead = route.find((step) => step.stage === "unit_head");
    const sanction = route.find((step) => step.stage === "sanction");
    const estt = route.find((step) => step.stage === "establishment");
    setHead(unitHead ? String(unitHead.user_id) : null);
    setFinal(sanction ? String(sanction.user_id) : null);
    setFinalRole(sanction?.role ?? "Registrar");
    setEstablishment(estt ? String(estt.user_id) : null);
  }, [employee, query.data?.employees]);
  async function save(path: string, data: unknown, method: "post" | "put" = "post") {
    try { await write.mutateAsync({path, data, method}); notifications.show({message:"Configuration saved."}); }
    catch(e) { notifications.show({color:"red",message:errorMessage(e)}); }
  }
  function saveEmployee() {
    const routes: Record<string,Step[]> = {};
    for (const c of eligible) {
      const self = designation === "Director" && employee === final && finalRole === "Director";
      routes[c] = self ? [{stage:"sanction",user_id:Number(employee),role:"Director"}] : [{stage:"unit_head",user_id:Number(head),role:"Unit Head"}];
      if (!self && !["CL","RH"].includes(c)) {
        if(establishment) routes[c].push({stage:"establishment",user_id:Number(establishment),role:"Deputy Registrar (Estt.)"});
        routes[c].push({stage:"sanction",user_id:Number(final),role:finalRole ?? "Registrar"});
      }
      const existing = query.data?.employees.find((row) => row.user_id === Number(employee));
      if (existing?.routes[c] && !routingChanged) {
        routes[c] = existing.routes[c];
        continue;
      }
      routes[c] = routes[c].map((step) => {
        const previous = existing?.routes[c]?.find((row) => row.stage === step.stage);
        return previous ? {...previous, ...step} : step;
      });
    }
    save("configuration/",{employee:{user_id:Number(employee),unit,designation,coverage_required:coverage,eligible_categories:eligible,routes}},"put");
  }
  if (!can("elm.configuration.manage")) return <Shell title="Leave Administration"><Text>Your active role cannot maintain leave configuration.</Text></Shell>;
  return <Shell title="Leave Administration">{query.error && <ErrorState error={query.error} />}
    <Card withBorder><Stack><Title order={4}>Current policy and SLA thresholds</Title><Text size="sm" c="dimmed">Current saved thresholds: {query.data?.policy ? `${query.data.policy.reminder_hours}h reminder / ${query.data.policy.escalation_hours}h escalation` : "Not configured"}</Text>
      <MultiSelect label="Non-working weekdays" value={weekdays} onChange={setWeekdays} data={["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"].map((d,i)=>({value:String(i),label:d}))} />
      <Checkbox label="Require medical evidence for COL" checked={medical} onChange={(e)=>setMedical(e.currentTarget.checked)} />
      <Group grow><NumberInput label="Reminder after hours" min={1} value={reminder} onChange={setReminder} /><NumberInput label="Escalation after hours" min={1} value={escalation} onChange={setEscalation} /></Group>
      <Button loading={write.isPending} onClick={()=>save("configuration/",{policy:{non_working_weekdays:weekdays.map(Number),require_col_evidence:medical,reminder_hours:Number(reminder),escalation_hours:Number(escalation)}},"put")}>Save policy</Button>
    </Stack></Card>
    <Card withBorder><Stack><Title order={4}>Employee eligibility and routing</Title><EmployeeChoice label="Employee" value={employee} onChange={setEmployee} />
      <Group grow><TextInput label="Organizational unit" value={unit} onChange={(e)=>setUnit(e.currentTarget.value)} /><TextInput label="Designation" value={designation} onChange={(e)=>{setDesignation(e.currentTarget.value); setRoutingChanged(true);}} /></Group>
      <MultiSelect label="Eligible leave categories" data={categories} value={eligible} onChange={setEligible} /><Checkbox label="Substitute coverage is required" checked={coverage} onChange={(e)=>setCoverage(e.currentTarget.checked)} />
      <EmployeeChoice label="Unit Head" value={head} onChange={(v)=>{setHead(v); setRoutingChanged(true);}} /><EmployeeChoice label="Establishment processor (optional)" value={establishment} onChange={(v)=>{setEstablishment(v); setRoutingChanged(true);}} />
      <EmployeeChoice label="Final sanctioning authority for SCL / EL / COL / VL" value={final} onChange={(v)=>{setFinal(v); setRoutingChanged(true);}} /><Select label="Final authority designation" value={finalRole} onChange={(v)=>{setFinalRole(v); setRoutingChanged(true);}} data={["Deputy Registrar (Estt.)","Dean","Registrar","Director"]} />
      <Button loading={write.isPending} onClick={saveEmployee}>Save employee hierarchy</Button>
      <Text size="sm" c="dimmed">{query.data?.employees.length ?? 0} employees configured. Assign the corresponding IAM designations before they process requests.</Text>
    </Stack></Card>
    <Card withBorder><Stack><Title order={4}>Holiday and restricted-holiday calendar</Title><NumberInput label="Year" value={year} onChange={setYear} min={1900} max={2200} />
      <Textarea label="Closed holidays, one YYYY-MM-DD date per line" value={holidays} onChange={(e)=>setHolidays(e.currentTarget.value)} /><Textarea label="Restricted holidays, one YYYY-MM-DD date per line" value={rh} onChange={(e)=>setRh(e.currentTarget.value)} />
      <Checkbox label="Publish this replacement calendar" checked={publish} onChange={(e)=>setPublish(e.currentTarget.checked)} /><Button loading={write.isPending} onClick={()=>save("calendars/",{year:Number(year),holidays:holidays.split(/\s+/).filter(Boolean),restricted_holidays:rh.split(/\s+/).filter(Boolean),published:publish})}>Save calendar</Button>
      {query.data?.calendars.map((c)=><Text size="sm" key={c.id}>{c.year} · revision #{c.id} · {c.published ? "Published" : "Draft / replaced"}</Text>)}
    </Stack></Card>
    <Alert title="External synchronization" color="blue">{query.data?.attendance_outbox.length ?? 0} attendance synchronization records await an external consumer. Vacation dates are supplied by the institute Academic Calendar.</Alert>
    {write.error && <ErrorState error={write.error} />}
  </Shell>;
}

export function LeaveRecords() {
  const {can} = useAuth();
  const allowed = can("elm.record.manage");
  const [path, setPath] = useState("applications/");
  const query = useElmQuery<Page<LeaveApplication>>(path, allowed);
  const write = useElmWrite();
  const [opened, setOpened] = useState(false);
  const [employee, setEmployee] = useState<string | null>(null);
  const [category, setCategory] = useState<string | null>("CL");
  const [start, setStart] = useState(""); const [end, setEnd] = useState("");
  const [half, setHalf] = useState<string | null>("full");
  const [reason, setReason] = useState(""); const [reference, setReference] = useState("");
  const [unavailable, setUnavailable] = useState(""); const [authority, setAuthority] = useState<string | null>(null);
  const [authorityRole, setAuthorityRole] = useState<string | null>("Unit Head");
  const [station, setStation] = useState(false); const [stationDetails, setStationDetails] = useState("");
  const [medical, setMedical] = useState("");
  const [correction, setCorrection] = useState<LeaveApplication | null>(null);
  const [correctedReference, setCorrectedReference] = useState(""); const [correctionReason, setCorrectionReason] = useState("");
  async function record() {
    try {
      await write.mutateAsync({path:"offline/", data:{user_id:Number(employee), category, start_date:start,
        end_date:end, half, reason, offline_reference:reference, unavailability_reason:unavailable,
        authority_id:Number(authority), authority_role:authorityRole, station_leave:station,
        station_details:stationDetails, medical_reference:medical}});
      setOpened(false); setReference(""); setReason(""); setUnavailable("");
      notifications.show({message:"Previously sanctioned leave recorded."});
    } catch(e) { notifications.show({color:"red", message:errorMessage(e)}); }
  }
  async function correct() {
    if (!correction) return;
    try {
      await write.mutateAsync({path:`applications/${correction.id}/correction/`,
        data:{reason:correctionReason, reference:correctedReference}});
      setCorrection(null); setCorrectionReason("");
      notifications.show({message:"Reference corrected; sanction and balances are unchanged."});
    } catch(e) { notifications.show({color:"red", message:errorMessage(e)}); }
  }
  if (!allowed) return <Shell title="Leave Records"><Text>Your active role cannot maintain leave records.</Text></Shell>;
  return <Shell title="Leave Records">
    <Group justify="space-between"><Text>Record existing offline sanctions and correct their references.</Text><Button onClick={()=>setOpened(true)}>Record offline-sanctioned leave</Button></Group>
    {query.error && <ErrorState error={query.error} />}{query.isPending && <Loader />}
    {query.data?.results.map((app)=><Card key={app.id} withBorder><Stack gap="xs">
      <Text fw={600}>Request #{app.id} · Employee {app.user_id} · {app.category} · {label(app.status)}</Text>
      <Text>{app.start_date} to {app.effective_end_date}</Text>
      <Text size="sm">Sanction reference: {app.offline_reference || "Online application"}</Text>
      <ApplicationCard app={app} />
      {app.offline_reference && <Button variant="light" onClick={()=>{setCorrection(app); setCorrectedReference(app.offline_reference);}}>Correct reference</Button>}
    </Stack></Card>)}
    {query.data && !query.data.results.length && <Text>No leave records yet.</Text>}
    <CursorControls page={query.data} onChange={setPath} />
    <Modal opened={opened} onClose={()=>setOpened(false)} title="Record existing offline sanction"><Stack>
      <Text size="sm">Use this only for leave already sanctioned through the authorized offline process. Recording does not request another approval.</Text>
      <EmployeeChoice label="Employee" value={employee} onChange={setEmployee} />
      <Select label="Leave category" data={categories} value={category} onChange={setCategory} />
      <Group grow><TextInput label="Start date" type="date" value={start} onChange={(e)=>setStart(e.currentTarget.value)} /><TextInput label="End date" type="date" value={end} onChange={(e)=>setEnd(e.currentTarget.value)} /></Group>
      <Select label="Day portion" data={[{value:"full",label:"Full day"},{value:"first",label:"First half (CL)"},{value:"second",label:"Second half (CL)"}]} value={half} onChange={setHalf} />
      <Textarea label="Leave purpose" value={reason} onChange={(e)=>setReason(e.currentTarget.value)} />
      <TextInput label="Existing sanction reference" value={reference} onChange={(e)=>setReference(e.currentTarget.value)} />
      <Textarea label="Why ELM was unavailable" value={unavailable} onChange={(e)=>setUnavailable(e.currentTarget.value)} />
      <EmployeeChoice label="Sanctioning authority" value={authority} onChange={setAuthority} />
      <Select label="Authority designation" value={authorityRole} onChange={setAuthorityRole} data={["Unit Head","Deputy Registrar (Estt.)","Dean","Registrar","Director"]} />
      <Checkbox label="Station Leave" checked={station} onChange={(e)=>setStation(e.currentTarget.checked)} />
      {station && <Textarea label="Station leave details" value={stationDetails} onChange={(e)=>setStationDetails(e.currentTarget.value)} />}
      {category === "COL" && <TextInput label="Medical evidence reference" value={medical} onChange={(e)=>setMedical(e.currentTarget.value)} />}
      {write.error && <ErrorState error={write.error} />}
      <Button loading={write.isPending} disabled={!employee || !authority || !start || !end || !reason.trim() || !reference.trim() || !unavailable.trim()} onClick={record}>Record sanctioned leave</Button>
    </Stack></Modal>
    <Modal opened={correction !== null} onClose={()=>setCorrection(null)} title="Correct offline sanction reference"><Stack>
      <TextInput label="Corrected reference" value={correctedReference} onChange={(e)=>setCorrectedReference(e.currentTarget.value)} />
      <Textarea label="Correction reason" value={correctionReason} onChange={(e)=>setCorrectionReason(e.currentTarget.value)} />
      <Button loading={write.isPending} disabled={!correctedReference.trim() || !correctionReason.trim()} onClick={correct}>Save reference correction</Button>
    </Stack></Modal>
  </Shell>;
}
