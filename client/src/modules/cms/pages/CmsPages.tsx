import { useMemo, useState } from "react";
import {
  Alert, Badge, Button, Card, Checkbox, Container, FileInput, Grid, Group,
  NumberInput, Paper, Select, SimpleGrid, Stack, Table, Text, TextInput,
  Textarea, Title,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { FaBullhorn, FaClipboardList, FaInbox, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAddProgress, useAssignCmsRole, useCmsAnnouncements, useCmsComplaints,
  useCmsConfig, useCmsEscalations, useCmsFeedback, useCmsReports, useCmsReopeningRequests,
  useCmsRoles, useComplaintOutcome, useEscalateComplaint, useHandlingSetup,
  usePublishCmsAnnouncement, useReopenComplaint, useReopeningDecision,
  useSubmitComplaint, useSubmitFeedback, useSupervisorClosure, useUserClosure,
} from "../api/hooks";
import type { CmsAnnouncement, CmsComplaint } from "../api/types";

const STATUS_OPTIONS = ["submitted", "in_progress", "resolved", "rejected", "closed"];
const PRIORITIES = [
  { value: "low", label: "Low" }, { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

function PageError({ error }: { error: unknown }) {
  return <Container size="xl"><ErrorState error={error} /></Container>;
}

function CmsTable<T>({ rows, cols, keyOf, empty }: {
  rows: T[]; cols: { label: string; render: (row: T) => React.ReactNode }[];
  keyOf: (row: T) => string | number; empty: string;
}) {
  if (!rows.length) return <Card withBorder padding="xl"><Stack align="center" gap="xs">
    <FaInbox color="var(--mantine-color-gray-5)" /><Text fw={600}>{empty}</Text>
  </Stack></Card>;
  return <Table.ScrollContainer minWidth={760} type="native"><Table striped highlightOnHover>
    <Table.Thead><Table.Tr>{cols.map((c) => <Table.Th key={c.label}>{c.label}</Table.Th>)}</Table.Tr></Table.Thead>
    <Table.Tbody>{rows.map((row) => <Table.Tr key={keyOf(row)}>
      {cols.map((c) => <Table.Td key={c.label}>{c.render(row)}</Table.Td>)}
    </Table.Tr>)}</Table.Tbody>
  </Table></Table.ScrollContainer>;
}

export function CmsHomePage() {
  const { can } = useAuth();
  const mine = useCmsComplaints({}, true, can("cms.complaint.track"));
  const reports = useCmsReports(can("cms.report.view"));
  if (mine.error) return <PageError error={mine.error} />;
  if (reports.error && can("cms.report.view")) return <PageError error={reports.error} />;
  const count = (reports.data?.by_status ?? []).reduce((n, row) => n + row.count, 0);
  return <Container size="xl">
    <PageHeader title="Complaint Management" subtitle="Track requests and keep complaint handling visible." />
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} mb="lg">
      <Metric label="My complaints" value={mine.data?.results.length ?? 0} />
      {can("cms.report.view") && <>
        <Metric label="Complaints in scope" value={count} />
        <Metric label="Unresolved" value={reports.data?.unresolved ?? 0} />
        <Metric label="Escalated" value={reports.data?.escalated ?? 0} />
      </>}
    </SimpleGrid>
    <Grid gutter="md">
      <Grid.Col span={{ base: 12, md: 7 }}>
        <Title order={4} mb="sm">Recent complaints</Title>
        <ComplaintTable rows={(mine.data?.results ?? []).slice(0, 5)} empty="No complaints submitted yet." />
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 5 }}>
        <Card withBorder padding="lg">
          <Group mb="sm"><FaClipboardList /><Text fw={700}>How CMS works</Text></Group>
          <Text size="sm" c="dimmed">Submit a complaint, follow its status and history, then verify the outcome or request reopening when available.</Text>
          <Text size="xs" c="dimmed" mt="sm">A complaint's assigned handler records progress and a resolution or rejection. CMS records notification events; message delivery is managed by platform services.</Text>
        </Card>
      </Grid.Col>
    </Grid>
  </Container>;
}

function Metric({ label, value }: { label: string; value: number }) {
  return <Card withBorder padding="md"><Text size="xs" c="dimmed">{label}</Text>
    <Text size="xl" fw={700}>{value}</Text></Card>;
}

function ComplaintTable({ rows, empty, action }: {
  rows: CmsComplaint[]; empty: string; action?: (row: CmsComplaint) => React.ReactNode;
}) {
  return <CmsTable rows={rows} keyOf={(r) => r.id} empty={empty} cols={[
    { label: "Complaint", render: (r) => <Stack gap={0}><Text fw={600}>{r.complaint_id}</Text><Text size="xs" c="dimmed">{r.category}</Text></Stack> },
    { label: "Status", render: (r) => <StatusBadge status={r.status} /> },
    { label: "Priority", render: (r) => r.priority ? <Badge variant="light">{r.priority}</Badge> : "—" },
    { label: "Submitted", render: (r) => new Date(r.created_at).toLocaleDateString() },
    ...(action ? [{ label: "Action", render: action }] : []),
  ]} />;
}

export function SubmitComplaintPage() {
  const config = useCmsConfig();
  const submit = useSubmitComplaint();
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [done, setDone] = useState<string | null>(null);
  const maxBytes = config.data?.attachment_max_bytes ?? 10 * 1024 * 1024;
  const maxCount = config.data?.attachment_max_count ?? 5;
  const allowed = config.data?.attachment_allowed_extensions ?? [
    ".pdf", ".png", ".jpg", ".jpeg", ".txt", ".docx",
  ];
  const tooLarge = files.some((f) => f.size > maxBytes);
  function save() {
    submit.mutate({ category: category.trim(), description: description.trim(), attachments: files }, {
      onSuccess: (complaint) => {
        setDone(complaint.complaint_id); setCategory(""); setDescription(""); setFiles([]);
        notifications.show({ color: "green", title: "Complaint submitted", message: `${complaint.complaint_id} is ready to track.` });
      },
      onError: (error) => notifications.show({ color: "red", title: "Submission failed", message: errorMessage(error) }),
    });
  }
  return <Container size="md">
    <PageHeader title="Submit a complaint" subtitle="Describe the issue so the Complaint Handler can review and assign it." />
    <Card withBorder padding="lg"><Stack>
      {done && <Alert color="green" title="Complaint received">Your reference is <b>{done}</b>. You can follow updates in My Complaints.</Alert>}
      <TextInput label="Category or type" required value={category} onChange={(e) => setCategory(e.currentTarget.value)} maxLength={120} description="Use the category that best describes the issue." />
      <Textarea label="Description" required minRows={5} autosize value={description} onChange={(e) => setDescription(e.currentTarget.value)} maxLength={10000} description="Include enough detail to understand the complaint." />
      <FileInput label="Supporting attachments" description={`Optional. Up to ${maxCount} files, ${Math.ceil(maxBytes / 1024 / 1024)} MB each. Allowed: ${allowed.join(", ")}.`} multiple value={files} onChange={(v) => setFiles(v ?? [])} accept={allowed.join(",")} />
      {tooLarge && <Text size="sm" c="red">Each attachment must be {Math.ceil(maxBytes / 1024 / 1024)} MB or smaller.</Text>}
      <Group justify="flex-end"><Button leftSection={<FaPlus size={12} />} onClick={save} loading={submit.isPending} disabled={!category.trim() || !description.trim() || tooLarge || files.length > maxCount}>Submit complaint</Button></Group>
    </Stack></Card>
  </Container>;
}

export function MyComplaintsPage() {
  const { data, isPending, error } = useCmsComplaints({}, true);
  const [selected, setSelected] = useState<CmsComplaint | null>(null);
  if (error) return <PageError error={error} />;
  return <Container size="xl">
    <PageHeader title="My Complaints" subtitle="Status, progress history and actions for complaints you submitted." />
    {isPending ? <Text c="dimmed">Loading complaints…</Text> : <ComplaintTable rows={data?.results ?? []} empty="No complaints submitted yet. Select Submit Complaint to start." action={(row) => <Button size="xs" variant="light" onClick={() => setSelected(row)}>View details</Button>} />}
    {data?.next && <Text size="xs" c="dimmed" mt="sm">Showing the first 100 results. Refine your view or use the API cursor for older records.</Text>}
    <ComplaintDetails complaint={selected} onClose={() => setSelected(null)} />
  </Container>;
}

export function WorklistPage() {
  const [status, setStatus] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const filters = useMemo(() => ({ ...(status ? { status } : {}), ...(query ? { q: query } : {}) }), [status, query]);
  const { data, isPending, error } = useCmsComplaints(filters);
  const [selected, setSelected] = useState<CmsComplaint | null>(null);
  if (error) return <PageError error={error} />;
  return <Container size="xl">
    <PageHeader title="Complaint Worklist" subtitle="Review submitted complaints, record handling and progress, and resolve or reject with a reason." action={<Group><TextInput aria-label="Search complaints" placeholder="Search reference or text" value={query} onChange={(e) => setQuery(e.currentTarget.value)} /><Select aria-label="Filter by status" placeholder="All statuses" clearable value={status} onChange={setStatus} data={STATUS_OPTIONS.map((x) => ({ value: x, label: x.replace(/_/g, " ") }))} w={170} /></Group>} />
    {isPending ? <Text c="dimmed">Loading worklist…</Text> : <ComplaintTable rows={data?.results ?? []} empty="No complaints match this worklist." action={(row) => <Button size="xs" variant="light" onClick={() => setSelected(row)}>Review</Button>} />}
    <ComplaintDetails complaint={selected} staff onClose={() => setSelected(null)} />
  </Container>;
}

function ComplaintDetails({ complaint, staff = false, onClose }: {
  complaint: CmsComplaint | null; staff?: boolean; onClose: () => void;
}) {
  const { can } = useAuth();
  const setup = useHandlingSetup(); const progress = useAddProgress();
  const outcome = useComplaintOutcome(); const escalation = useEscalateComplaint();
  const closeUser = useUserClosure(); const closeSupervisor = useSupervisorClosure();
  const reopen = useReopenComplaint(); const feedback = useSubmitFeedback();
  const [category, setCategory] = useState(complaint?.category ?? "");
  const [priority, setPriority] = useState<string | null>(complaint?.priority || null);
  const [progressText, setProgressText] = useState("");
  const [outcomeText, setOutcomeText] = useState("");
  const [reopenText, setReopenText] = useState("");
  const [feedbackText, setFeedbackText] = useState("");
  const [assignmentNote, setAssignmentNote] = useState("");
  const [outcomeChoice, setOutcomeChoice] = useState<string | null>(null);
  const busy = setup.isPending || progress.isPending || outcome.isPending || escalation.isPending
    || closeUser.isPending || closeSupervisor.isPending || reopen.isPending || feedback.isPending;
  const run = (fn: (opts: { onSuccess: () => void; onError: (e: unknown) => void }) => void) => fn({
    onSuccess: () => { notifications.show({ color: "green", title: "Saved", message: "The complaint record was updated." }); onClose(); },
    onError: (e) => notifications.show({ color: "red", title: "Action failed", message: errorMessage(e) }),
  });
  if (!complaint) return null;
  const own = !staff;
  const canSetup = staff && can("cms.complaint.assign") && !complaint.assigned_handler_user_id && complaint.status === "submitted";
  const canProgress = staff && can("cms.complaint.update") && complaint.assigned_handler_user_id != null && ["submitted", "in_progress"].includes(complaint.status);
  const canOutcome = staff && can("cms.complaint.resolve") && complaint.assigned_handler_user_id != null && ["submitted", "in_progress"].includes(complaint.status);
  const canEscalate = staff && can("cms.escalation.manual") && !complaint.escalated && ["submitted", "in_progress"].includes(complaint.status);
  const canClose = complaint.status === "resolved" && ((own && complaint.closure_verifier === "complainant" && can("cms.close.user")) || (staff && complaint.closure_verifier === "supervisor" && can("cms.close.supervisor")));
  const canReopen = own && complaint.status === "closed" && can("cms.complaint.reopen");
  const canLeaveFeedback = own && ["resolved", "closed"].includes(complaint.status) && can("cms.feedback.submit");
  return <FormModal opened onClose={onClose} title={complaint.complaint_id} subtitle={`${complaint.category} · ${complaint.status.replace(/_/g, " ")}`} onSubmit={onClose} submitLabel="Close" submitting={busy} size="xl">
    <Stack>
      <Group><StatusBadge status={complaint.status} />{complaint.priority && <Badge variant="light">{complaint.priority} priority</Badge>}{complaint.escalated && <Badge color="orange">Escalated · {complaint.escalation_kind}</Badge>}</Group>
      <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{complaint.description}</Text>
      {complaint.resolution_details && <Alert color="green" title="Resolution">{complaint.resolution_details}</Alert>}
      {complaint.rejection_reason && <Alert color="red" title="Rejection reason">{complaint.rejection_reason}</Alert>}
      {!!complaint.attachments.length && <Stack gap={4}><Text fw={600} size="sm">Attachments</Text>{complaint.attachments.map((file) => <Button key={file.id} component="a" href={file.download_url} variant="subtle" size="xs" target="_blank">{file.file_name}</Button>)}</Stack>}
      <Title order={5}>History</Title>
      {complaint.history.map((row, i) => <Paper key={`${row.to_status}-${i}`} withBorder p="xs"><Group justify="space-between"><Text size="sm" fw={600}>{row.from_status ? `${row.from_status.replace(/_/g, " ")} → ` : ""}{row.to_status.replace(/_/g, " ")}</Text><Text size="xs" c="dimmed">{new Date(row.created_at).toLocaleString()}</Text></Group>{row.note && <Text size="sm" mt={4}>{row.note}</Text>}</Paper>)}
      {!!complaint.progress_updates.length && <><Title order={5}>Progress updates</Title>{complaint.progress_updates.map((row) => <Paper key={row.id} withBorder p="xs"><Text size="sm">{row.update_text}</Text><Text size="xs" c="dimmed">{new Date(row.created_at).toLocaleString()}</Text></Paper>)}</>}
      {canSetup && <Paper withBorder p="md"><Title order={5} mb="sm">Assign and prioritize</Title><Stack><TextInput label="Category or type" required value={category} onChange={(e) => setCategory(e.currentTarget.value)} /><Select label="Priority" required value={priority} onChange={setPriority} data={PRIORITIES} /><Textarea label="Assignment note" value={assignmentNote} onChange={(e) => setAssignmentNote(e.currentTarget.value)} /><Button loading={setup.isPending} disabled={!priority || !category.trim()} onClick={() => run((opts) => setup.mutate({ id: complaint.id, body: { category, priority: priority!, note: assignmentNote } }, opts))}>Save handling setup</Button></Stack></Paper>}
      {canProgress && <Paper withBorder p="md"><Title order={5} mb="sm">Add progress update</Title><Stack><Textarea value={progressText} onChange={(e) => setProgressText(e.currentTarget.value)} label="Update" required minRows={2} /><Button loading={progress.isPending} disabled={!progressText.trim()} onClick={() => run((opts) => progress.mutate({ id: complaint.id, body: { text: progressText } }, opts))}>Record progress</Button></Stack></Paper>}
      {canOutcome && <Paper withBorder p="md"><Title order={5} mb="sm">Record outcome</Title><Stack><Select label="Outcome" value={outcomeChoice} onChange={setOutcomeChoice} data={[{ value: "resolved", label: "Resolve" }, { value: "rejected", label: "Reject" }]} /><Textarea label={outcomeChoice === "rejected" ? "Rejection reason" : "Resolution details"} required value={outcomeText} onChange={(e) => setOutcomeText(e.currentTarget.value)} minRows={2} /><Button color={outcomeChoice === "rejected" ? "red" : undefined} loading={outcome.isPending} disabled={!outcomeChoice || !outcomeText.trim()} onClick={() => run((opts) => outcome.mutate({ id: complaint.id, body: { outcome: outcomeChoice as "resolved" | "rejected", details: outcomeText } }, opts))}>Save outcome</Button></Stack></Paper>}
      {canEscalate && <Button color="orange" variant="light" loading={escalation.isPending} onClick={() => run((opts) => escalation.mutate({ id: complaint.id, body: {} }, opts))}>Escalate complaint</Button>}
      {canClose && <Button loading={closeUser.isPending || closeSupervisor.isPending} onClick={() => run((opts) => own ? closeUser.mutate({ id: complaint.id, body: {} }, opts) : closeSupervisor.mutate({ id: complaint.id, body: {} }, opts))}>Verify and close</Button>}
      {canReopen && <Paper withBorder p="md"><Title order={5} mb="sm">Request reopening</Title><Stack><Textarea label="Why are you dissatisfied with the closure?" value={reopenText} onChange={(e) => setReopenText(e.currentTarget.value)} required minRows={2} /><Button loading={reopen.isPending} disabled={!reopenText.trim()} onClick={() => run((opts) => reopen.mutate({ id: complaint.id, body: { text: reopenText } }, opts))}>Send reopening request</Button></Stack></Paper>}
      {canLeaveFeedback && <Paper withBorder p="md"><Title order={5} mb="sm">Leave feedback</Title><Stack><Textarea label="Feedback" value={feedbackText} onChange={(e) => setFeedbackText(e.currentTarget.value)} required minRows={2} /><Button loading={feedback.isPending} disabled={!feedbackText.trim()} onClick={() => run((opts) => feedback.mutate({ id: complaint.id, body: { text: feedbackText } }, opts))}>Submit feedback</Button></Stack></Paper>}
    </Stack>
  </FormModal>;
}

export function EscalationsPage() {
  const { data, isPending, error } = useCmsEscalations();
  if (error) return <PageError error={error} />;
  return <Container size="xl"><PageHeader title="Escalated Complaints" subtitle="Monitor manual and SLA-triggered escalations." />
    {isPending ? <Text c="dimmed">Loading escalations…</Text> : <ComplaintTable rows={data?.results ?? []} empty="No complaints have been escalated." />}
  </Container>;
}

export function ReopeningReviewPage() {
  const { data, isPending, error } = useCmsReopeningRequests();
  const decide = useReopeningDecision(); const [notes, setNotes] = useState<Record<number, string>>({});
  if (error) return <PageError error={error} />;
  const rows = data?.results ?? [];
  return <Container size="xl"><PageHeader title="Reopening Requests" subtitle="Review dissatisfied complainants' requests and record the decision." />
    {isPending ? <Text c="dimmed">Loading requests…</Text> : <CmsTable rows={rows} keyOf={(r) => r.id} empty="There are no pending reopening requests." cols={[
      { label: "Complaint", render: (r) => r.complaint },
      { label: "Reason", render: (r) => r.request_reason },
      { label: "Requested", render: (r) => new Date(r.created_at).toLocaleString() },
      { label: "Decision note", render: (r) => <TextInput aria-label={`Decision note ${r.id}`} value={notes[r.id] ?? ""} onChange={(e) => setNotes({ ...notes, [r.id]: e.currentTarget.value })} /> },
      { label: "Actions", render: (r) => <Group gap="xs"><Button size="xs" loading={decide.isPending} onClick={() => decide.mutate({ id: r.id, body: { decision: "approved", note: notes[r.id] ?? "" } }, { onError: (e) => notifications.show({ color: "red", title: "Could not approve", message: errorMessage(e) }) })}>Approve</Button><Button size="xs" color="red" variant="light" loading={decide.isPending} onClick={() => decide.mutate({ id: r.id, body: { decision: "denied", note: notes[r.id] ?? "" } }, { onError: (e) => notifications.show({ color: "red", title: "Could not deny", message: errorMessage(e) }) })}>Deny</Button></Group> },
    ]} />}
  </Container>;
}

export function FeedbackPage() {
  const { data, isPending, error } = useCmsFeedback();
  if (error) return <PageError error={error} />;
  return <Container size="xl"><PageHeader title="Submitted Feedback" subtitle="Feedback from resolved or closed complaints." />
    {isPending ? <Text c="dimmed">Loading feedback…</Text> : <CmsTable rows={data?.results ?? []} keyOf={(r) => r.id} empty="No feedback has been submitted." cols={[
      { label: "Complaint", render: (r) => r.complaint }, { label: "Feedback", render: (r) => r.feedback_text },
      { label: "Submitted", render: (r) => new Date(r.created_at).toLocaleString() },
    ]} />}
  </Container>;
}

export function AnnouncementsPage() {
  const { can } = useAuth(); const { data, isPending, error } = useCmsAnnouncements();
  const publish = usePublishCmsAnnouncement(); const [title, setTitle] = useState("");
  const [body, setBody] = useState(""); const [notify, setNotify] = useState(false);
  if (error) return <PageError error={error} />;
  function save() { publish.mutate({ body: { title: title.trim(), body: body.trim(), notify_users: notify } }, {
    onSuccess: () => { setTitle(""); setBody(""); setNotify(false); notifications.show({ color: "green", title: "Announcement published", message: "The announcement is now visible to CMS users." }); },
    onError: (e) => notifications.show({ color: "red", title: "Could not publish", message: errorMessage(e) }),
  }); }
  const rows = data?.results ?? [];
  return <Container size="lg"><PageHeader title="Announcements" subtitle="Complaint-related notices shared with CMS users." />
    {can("cms.announcement.publish") && <Card withBorder mb="lg"><Stack><Title order={4}>Publish an announcement</Title><TextInput label="Title" required value={title} onChange={(e) => setTitle(e.currentTarget.value)} maxLength={200} /><Textarea label="Announcement" required value={body} onChange={(e) => setBody(e.currentTarget.value)} minRows={3} /><Checkbox label="Trigger the configured announcement notification" checked={notify} onChange={(e) => setNotify(e.currentTarget.checked)} /><Group justify="flex-end"><Button loading={publish.isPending} disabled={!title.trim() || !body.trim()} onClick={save}>Publish</Button></Group></Stack></Card>}
    {isPending ? <Text c="dimmed">Loading announcements…</Text> : rows.length ? <Stack>{rows.map((item: CmsAnnouncement) => <Card key={item.id} withBorder><Group justify="space-between"><Text fw={700}>{item.title}</Text><Text size="xs" c="dimmed">{new Date(item.published_at).toLocaleString()}</Text></Group><Text mt="sm" style={{ whiteSpace: "pre-wrap" }}>{item.body}</Text></Card>)}</Stack> : <Card withBorder padding="xl"><Stack align="center"><FaBullhorn color="var(--mantine-color-gray-5)" /><Text fw={600}>No announcements yet</Text></Stack></Card>}
  </Container>;
}

export function ReportsPage() {
  const { data, isPending, error } = useCmsReports();
  if (error) return <PageError error={error} />;
  return <Container size="xl"><PageHeader title="Reports & Analytics" subtitle="Complaint volume and escalation summaries available within CMS." />
    {isPending ? <Text c="dimmed">Loading reports…</Text> : <>
      <SimpleGrid cols={{ base: 2, sm: 4 }} mb="lg"><Metric label="Total complaints" value={data?.total ?? 0} /><Metric label="Unresolved" value={data?.unresolved ?? 0} /><Metric label="Escalated" value={data?.escalated ?? 0} /><Metric label="Categories" value={data?.by_category.length ?? 0} /></SimpleGrid>
      <Grid gutter="lg"><Grid.Col span={{ base: 12, md: 6 }}><Title order={4} mb="sm">By status</Title><SummaryRows rows={(data?.by_status ?? []).map((x) => [x.status.replace(/_/g, " "), x.count])} /></Grid.Col><Grid.Col span={{ base: 12, md: 6 }}><Title order={4} mb="sm">By priority</Title><SummaryRows rows={(data?.by_priority ?? []).map((x) => [x.priority || "Unassigned", x.count])} /></Grid.Col><Grid.Col span={12}><Title order={4} mb="sm">Operational report by category</Title><SummaryRows rows={(data?.by_category ?? []).map((x) => [x.category, x.count])} empty="No category data is available." /></Grid.Col></Grid>
      {data?.oldest_unresolved_at && <Text size="sm" c="dimmed" mt="lg">Oldest unresolved complaint submitted {new Date(data.oldest_unresolved_at).toLocaleString()}.</Text>}
    </>}
  </Container>;
}

function SummaryRows({ rows, empty = "No report data is available." }: { rows: (string | number)[][]; empty?: string }) {
  return rows.length ? <Table withTableBorder><Table.Tbody>{rows.map(([label, value]) => <Table.Tr key={String(label)}><Table.Td>{label}</Table.Td><Table.Td ta="right" fw={700}>{value}</Table.Td></Table.Tr>)}</Table.Tbody></Table> : <Text c="dimmed">{empty}</Text>;
}

export function CmsRolesPage() {
  const roles = useCmsRoles(); const assign = useAssignCmsRole();
  const [role, setRole] = useState<string | null>("handler"); const [userId, setUserId] = useState<number | string>("");
  const [starts, setStarts] = useState<Date | null>(new Date()); const [ends, setEnds] = useState<Date | null>(null);
  if (roles.error) return <PageError error={roles.error} />;
  function save() {
    if (!role || !starts || !ends || userId === "") return;
    assign.mutate({ body: { role: role as "handler" | "supervisor", user_id: Number(userId), starts_at: starts.toISOString(), ends_at: ends.toISOString() } }, {
      onSuccess: () => { setUserId(""); notifications.show({ color: "green", title: "CMS role assigned", message: "The existing appointment was replaced for this role." }); },
      onError: (e) => notifications.show({ color: "red", title: "Could not assign role", message: errorMessage(e) }),
    });
  }
  return <Container size="lg"><PageHeader title="CMS Role Management" subtitle="Assign the single Complaint Handler and Complaint Supervisor appointment for a specified period." />
    <Alert color="blue" mb="md" title="IAM owns institutional users">Enter the user ID of an existing institutional account. CMS stores only the CMS appointment; it does not create or edit user accounts.</Alert>
    <Card withBorder padding="lg" mb="lg"><Stack><Select label="CMS role" value={role} onChange={setRole} data={[{ value: "handler", label: "Complaint Handler" }, { value: "supervisor", label: "Complaint Supervisor" }]} /><NumberInput label="Institutional user ID" value={userId} onChange={setUserId} min={1} required /><DateTimePicker label="Starts at" value={starts} onChange={setStarts} required /><DateTimePicker label="Ends at" value={ends} onChange={setEnds} required /><Group justify="flex-end"><Button loading={assign.isPending} disabled={!role || !userId || !starts || !ends || starts >= ends} onClick={save}>Assign / reassign role</Button></Group></Stack></Card>
    <Title order={4} mb="sm">Current appointments</Title>
    {roles.isPending ? <Text c="dimmed">Loading appointments…</Text> : <CmsTable rows={roles.data ?? []} keyOf={(r) => r.role} empty="No active CMS role appointments." cols={[
      { label: "Role", render: (r) => r.role === "handler" ? "Complaint Handler" : "Complaint Supervisor" },
      { label: "User ID", render: (r) => r.user_id }, { label: "Starts", render: (r) => new Date(r.starts_at).toLocaleString() },
      { label: "Expires", render: (r) => new Date(r.ends_at).toLocaleString() },
    ]} />}
  </Container>;
}
