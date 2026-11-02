/* eslint-disable react/prop-types */
import { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Container,
  FileInput,
  Grid,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { FaArchive, FaBell, FaCheckCircle, FaDatabase, FaExclamationTriangle, FaHdd, FaLock, FaRedo, FaShieldAlt } from "react-icons/fa";
import PageHeader from "../../components/PageHeader/PageHeader";
import {
  createArchiveRequest,
  createRestoreRequest,
  createStorageRequest,
  decideApproval,
  fetchApprovalQueue,
  fetchFailureAlerts,
  fetchArchiveRequests,
  fetchRestoreRequests,
  fetchSecurityAuditLogs,
  fetchSecurityStatus,
  fetchStorageRequests,
} from "../../api/BADMS";
import { fetchBackups } from "../../api/Backups";

const records = (value) => Array.isArray(value) ? value : value?.results || value?.items || [];
const dateLabel = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
};
const errorMessage = (error, fallback) => {
  const data = error?.response?.data;
  const detail = data?.detail ?? data?.message ?? data?.errors;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) return detail.map(String).join("; ");
  if (detail && typeof detail === "object") {
    return Object.entries(detail)
      .map(([field, messages]) => `${field}: ${Array.isArray(messages) ? messages.join(", ") : String(messages)}`)
      .join("; ") || fallback;
  }
  return fallback;
};
const statusColor = (value = "submitted") => ({
  submitted: "blue", pending: "yellow", pending_hod: "yellow", pending_sysadmin: "orange",
  pending_it_security: "violet", approved: "green", rejected: "red", completed: "green",
  failed: "red", in_progress: "cyan", in_review: "orange",
}[String(value).toLowerCase()] || "gray");
const Status = ({ value }) => <Badge color={statusColor(value)} variant="light">{String(value || "unknown").replaceAll("_", " ")}</Badge>;
const ErrorMessage = ({ error, fallback }) => error ? <Alert color="red" title="Unable to load data">{errorMessage(error, fallback)}</Alert> : null;
const Loading = ({ active, children }) => active ? <Center py="xl"><Loader /></Center> : children;
const notifySuccess = (message) => notifications.show({ title: "Submitted", message, color: "green" });
const notifyError = (error, message) => notifications.show({ title: "Request failed", message: errorMessage(error, message), color: "red" });

export function ArchiveRequestsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const form = useForm({
    initialValues: {
      file_name: "", archive_date: new Date().toISOString().slice(0, 10), owners: "",
      file_type: "document", reason: "", attachment: null, initial_classification: "Routine",
    },
    validate: {
      file_name: (v) => v.trim() ? null : "Enter the file or record name",
      archive_date: (v) => v ? null : "Select the archive date",
      owners: (v) => v.trim() ? null : "Enter the record owner(s)",
      reason: (v) => v.trim().length >= 10 ? null : "Provide a reason of at least 10 characters",
    },
  });
  const load = useCallback(async () => {
    setLoading(true); setLoadError(null);
    try { setItems(records(await fetchArchiveRequests())); }
    catch (error) { setLoadError(error); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const submit = async (values) => {
    setSaving(true);
    try {
      await createArchiveRequest(values);
      notifySuccess("Your archival request has been submitted for review.");
      form.reset();
      form.setFieldValue("archive_date", new Date().toISOString().slice(0, 10));
      form.setFieldValue("initial_classification", "Routine");
      load();
    } catch (error) { notifyError(error, "Could not submit the archival request."); }
    finally { setSaving(false); }
  };
  return <Container size="xl">
    <PageHeader title="Archive Request" subtitle="Submit a record for controlled archival and track its approval stages." />
    <Grid align="start">
      <Grid.Col span={{ base: 12, lg: 5 }}>
        <Card withBorder radius="md" p="lg">
          <Group mb="md"><FaArchive /><Title order={4}>New archival request</Title></Group>
          <form onSubmit={form.onSubmit(submit)}>
            <Stack>
              <TextInput label="File / record name" placeholder="e.g. 2024 examination records" required {...form.getInputProps("file_name")} />
              <TextInput type="date" label="Archive date" required {...form.getInputProps("archive_date")} />
              <TextInput label="Owner(s) / department" placeholder="Record owner or department" required {...form.getInputProps("owners")} />
              <Select label="File type" data={[{ value: "document", label: "Document" }, { value: "database", label: "Database" }, { value: "image", label: "Image" }, { value: "other", label: "Other" }]} {...form.getInputProps("file_type")} />
              <Select label="Initial classification" description="If no classification is supplied, the request defaults to Routine." data={[{ value: "Routine", label: "Routine" }, { value: "Sensitive", label: "Sensitive" }]} {...form.getInputProps("initial_classification")} />
              <Textarea label="Reason for archival" minRows={3} required {...form.getInputProps("reason")} />
              <FileInput label="Supporting attachment" placeholder="Choose a file (optional)" clearable accept=".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.zip" {...form.getInputProps("attachment")} />
              <Alert color="blue" variant="light">After submission, the request is routed to the HoD of the same department. SysAdmin verifies the authoritative classification. Sensitive records continue to IT Security for the AES-256 security path.</Alert>
              <Button type="submit" loading={saving} leftSection={<FaArchive />}>Submit archival request</Button>
            </Stack>
          </form>
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, lg: 7 }}>
        <Card withBorder radius="md" p="lg">
          <Group justify="space-between" mb="md"><Title order={4}>My archival requests</Title><Button variant="light" onClick={load}>Refresh</Button></Group>
          <ErrorMessage error={loadError} fallback="Check the BADMS archive-request API." />
          <Loading active={loading}>{items.length ? <Table.ScrollContainer minWidth={700}><Table striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>Record</Table.Th><Table.Th>Owner</Table.Th><Table.Th>Classification</Table.Th><Table.Th>Submitted</Table.Th><Table.Th>Stage / status</Table.Th></Table.Tr></Table.Thead><Table.Tbody>
            {items.map((item) => <Table.Tr key={item.id}><Table.Td>{item.file_name || item.record_name || "—"}</Table.Td><Table.Td>{item.owners || item.department || "—"}</Table.Td><Table.Td><Badge color={item.classification === "Sensitive" ? "violet" : "gray"}>{item.classification || item.initial_classification || "Routine"}</Badge></Table.Td><Table.Td>{dateLabel(item.created_at || item.submitted_at)}</Table.Td><Table.Td><Stack gap={4}><Status value={item.status} /><Text size="xs" c="dimmed">{item.current_stage || item.pending_with || "—"}</Text></Stack></Table.Td></Table.Tr>)}
          </Table.Tbody></Table></Table.ScrollContainer> : <Text c="dimmed" ta="center" py="xl">No archival requests submitted yet.</Text>}</Loading>
        </Card>
      </Grid.Col>
    </Grid>
  </Container>;
}

export function ApprovalQueuePage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [decision, setDecision] = useState("approve");
  const [comments, setComments] = useState("");
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const load = useCallback(async () => {
    setLoading(true); setLoadError(null);
    try { setItems(records(await fetchApprovalQueue())); }
    catch (error) { setLoadError(error); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const closeReview = () => {
    if (saving) return;
    setSelected(null);
    setDecision("approve");
    setComments("");
  };
  const openReview = (item) => {
    setDecision("approve");
    setComments("");
    setSelected(item);
  };
  const submitDecision = async () => {
    if (!selected || saving) return;
    if (decision === "reject" && !comments.trim()) {
      notifications.show({ title: "Comment required", message: "Add a reason before rejecting this request.", color: "orange" });
      return;
    }
    setSaving(true);
    try {
      // The server derives the actor's role and valid workflow stage from the session.
      await decideApproval(selected.id, { decision, comments: comments.trim() });
      notifySuccess(`Request ${decision === "approve" ? "approved" : "rejected"}.`);
      setSelected(null);
      setDecision("approve");
      setComments("");
      await load();
    } catch (error) { notifyError(error, "Could not save the approval decision."); }
    finally { setSaving(false); }
  };
  return <Container size="xl">
    <PageHeader title="Approval Queue" subtitle="Review requests assigned to your role and department." />
    <Alert color="blue" mb="md" variant="light">HoD decisions are limited to requests from the same department. SysAdmin confirms classification. IT Security reviews Sensitive archival requests. The backend must enforce these role and department checks.</Alert>
    <Card withBorder p="lg" radius="md">
      <Group justify="space-between" mb="md"><Title order={4}>Requests awaiting my action</Title><Button variant="light" onClick={load}>Refresh</Button></Group>
      <ErrorMessage error={loadError} fallback="Check the BADMS approval-queue API." />
      <Loading active={loading}>{items.length ? <Table.ScrollContainer minWidth={760}><Table striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>Request</Table.Th><Table.Th>Type</Table.Th><Table.Th>Department</Table.Th><Table.Th>Classification</Table.Th><Table.Th>Current stage</Table.Th><Table.Th>Submitted</Table.Th><Table.Th /></Table.Tr></Table.Thead><Table.Tbody>
        {items.map((item) => <Table.Tr key={item.id}><Table.Td>{item.file_name || item.title || `Request #${item.id}`}</Table.Td><Table.Td>{item.request_type || "Archive"}</Table.Td><Table.Td>{item.department || "—"}</Table.Td><Table.Td>{item.classification || "Routine"}</Table.Td><Table.Td><Status value={item.current_stage || item.status} /></Table.Td><Table.Td>{dateLabel(item.created_at || item.submitted_at)}</Table.Td><Table.Td><Button size="xs" onClick={() => openReview(item)}>Review</Button></Table.Td></Table.Tr>)}
      </Table.Tbody></Table></Table.ScrollContainer> : <Text c="dimmed" ta="center" py="xl">No requests are currently assigned to you.</Text>}</Loading>
    </Card>
    <Modal opened={Boolean(selected)} onClose={closeReview} title="Review BADMS request" centered>
      {selected && <Stack>
        <Text fw={600}>{selected.file_name || selected.title || `Request #${selected.id}`}</Text>
        <Text size="sm" c="dimmed">{selected.reason || selected.description || "No reason supplied."}</Text>
        <Group><Text size="sm">Classification:</Text><Badge color={selected.classification === "Sensitive" ? "violet" : "gray"}>{selected.classification || "Routine"}</Badge></Group>
        <Text size="sm">Current workflow stage: <b>{selected.current_stage || selected.status || "Pending"}</b></Text>
        <Select label="Decision" value={decision} onChange={setDecision} data={[{ value: "approve", label: "Approve / forward to next stage" }, { value: "reject", label: "Reject request" }]} />
        <Textarea label="Review comments" value={comments} onChange={(event) => setComments(event.currentTarget.value)} placeholder={decision === "reject" ? "Explain why this request is being rejected" : "Optional review notes"} required={decision === "reject"} error={decision === "reject" && !comments.trim() ? "A rejection reason is required" : null} />
        <Alert color="yellow" variant="light">Approval only advances the request to the next permitted stage. It does not directly archive or restore data.</Alert>
        <Group justify="flex-end"><Button variant="default" onClick={closeReview} disabled={saving}>Cancel</Button><Button color={decision === "approve" ? "green" : "red"} loading={saving} onClick={submitDecision}>{decision === "approve" ? "Approve / forward" : "Reject"}</Button></Group>
      </Stack>}
    </Modal>
  </Container>;
}

export function RestoreRequestsPage() {
  const [backups, setBackups] = useState([]);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const form = useForm({ initialValues: { backup_id: "", target_database: "", classification: "Routine", reason: "" }, validate: {
    backup_id: (v) => v ? null : "Select a backup",
    target_database: (v) => v.trim() ? null : "Enter the target database",
    reason: (v) => v.trim().length >= 10 ? null : "Provide a reason of at least 10 characters",
  } });
  const load = useCallback(async () => {
    setLoading(true); setLoadError(null);
    try {
      const [backupData, restoreData] = await Promise.all([fetchBackups(), fetchRestoreRequests()]);
      setBackups(records(backupData).filter((backup) => backup.status === "success"));
      setItems(records(restoreData));
    } catch (error) { setLoadError(error); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const submit = async (values) => {
    setSaving(true);
    try {
      await createRestoreRequest(values);
      notifySuccess(values.classification === "Sensitive" ? "Sensitive restoration request submitted for SysAdmin approval." : "Restoration request submitted through the standard approval path.");
      form.reset(); load();
    } catch (error) { notifyError(error, "Could not submit restoration request."); }
    finally { setSaving(false); }
  };
  return <Container size="xl">
    <PageHeader title="Restoration Requests" subtitle="Request restoration from an existing backup without bypassing the approval workflow." />
    <Grid align="start">
      <Grid.Col span={{ base: 12, lg: 5 }}><Card withBorder p="lg" radius="md"><Group mb="md"><FaRedo /><Title order={4}>New restoration request</Title></Group>
        <form onSubmit={form.onSubmit(submit)}><Stack>
          <Select searchable label="Source backup" placeholder="Choose a successful backup" data={backups.map((backup) => ({ value: String(backup.id), label: `${backup.db_name || backup.database_name || "Database"} · ${dateLabel(backup.created_at)}` }))} {...form.getInputProps("backup_id")} />
          <TextInput label="Target database" {...form.getInputProps("target_database")} />
          <Select label="Data classification" data={[{ value: "Routine", label: "Routine / non-Sensitive" }, { value: "Sensitive", label: "Sensitive" }]} {...form.getInputProps("classification")} />
          <Textarea label="Reason for restoration" minRows={3} {...form.getInputProps("reason")} />
          <Alert color="orange" variant="light">Routine restoration follows the standard approval path. Sensitive restoration requires SysAdmin approval before execution.</Alert>
          <Button type="submit" loading={saving}>Submit restoration request</Button>
        </Stack></form>
      </Card></Grid.Col>
      <Grid.Col span={{ base: 12, lg: 7 }}><Card withBorder p="lg" radius="md"><Group justify="space-between" mb="md"><Title order={4}>Restoration history</Title><Button variant="light" onClick={load}>Refresh</Button></Group>
        <ErrorMessage error={loadError} fallback="Check the BADMS restore-request API." />
        <Loading active={loading}>{items.length ? <Table.ScrollContainer minWidth={650}><Table striped><Table.Thead><Table.Tr><Table.Th>Target</Table.Th><Table.Th>Backup</Table.Th><Table.Th>Classification</Table.Th><Table.Th>Requested</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => <Table.Tr key={item.id}><Table.Td>{item.target_database || "—"}</Table.Td><Table.Td>{item.backup_id || "—"}</Table.Td><Table.Td>{item.classification || "Routine"}</Table.Td><Table.Td>{dateLabel(item.created_at || item.submitted_at)}</Table.Td><Table.Td><Status value={item.status} /></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer> : <Text c="dimmed" ta="center" py="xl">No restoration requests found.</Text>}</Loading>
      </Card></Grid.Col>
    </Grid>
  </Container>;
}

export function StorageRequestsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const form = useForm({ initialValues: { current_storage_gb: 0, requested_storage_gb: 0, reason: "" }, validate: {
    current_storage_gb: (value) => Number.isFinite(Number(value)) && Number(value) >= 0 ? null : "Enter a valid current capacity",
    requested_storage_gb: (value, values) => Number.isFinite(Number(value)) && Number(value) > Number(values.current_storage_gb) ? null : "Requested capacity must exceed current capacity",
    reason: (value) => value.trim().length >= 10 ? null : "Provide a reason of at least 10 characters",
  } });
  const load = useCallback(async () => { setLoading(true); setLoadError(null); try { setItems(records(await fetchStorageRequests())); } catch (error) { setLoadError(error); } finally { setLoading(false); } }, []);
  useEffect(() => { load(); }, [load]);
  const submit = async (values) => { setSaving(true); try { await createStorageRequest(values); notifySuccess("Storage extension request submitted to your HoD."); form.reset(); load(); } catch (error) { notifyError(error, "Could not submit storage request."); } finally { setSaving(false); } };
  return <Container size="xl"><PageHeader title="Storage Extension" subtitle="Request additional capacity when the allocated storage quota is exhausted." />
    <Grid align="start"><Grid.Col span={{ base: 12, lg: 5 }}><Card withBorder p="lg"><Group mb="md"><FaHdd /><Title order={4}>New storage request</Title></Group><form onSubmit={form.onSubmit(submit)}><Stack>
      <NumberInput label="Current allocated capacity (GB)" min={0} required {...form.getInputProps("current_storage_gb")} />
      <NumberInput label="Requested capacity (GB)" min={1} required {...form.getInputProps("requested_storage_gb")} />
      <Textarea label="Justification" minRows={3} required {...form.getInputProps("reason")} />
      <Alert color="blue" variant="light">The request is submitted to the HoD for a decision. Submit only when the current quota is full.</Alert>
      <Button type="submit" loading={saving}>Submit storage request</Button>
    </Stack></form></Card></Grid.Col>
    <Grid.Col span={{ base: 12, lg: 7 }}><Card withBorder p="lg"><Group justify="space-between" mb="md"><Title order={4}>My requests</Title><Button variant="light" onClick={load}>Refresh</Button></Group>
      <ErrorMessage error={loadError} fallback="Check the BADMS storage-request API." />
      <Loading active={loading}>{items.length ? <Table><Table.Thead><Table.Tr><Table.Th>Current</Table.Th><Table.Th>Requested</Table.Th><Table.Th>Submitted</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => <Table.Tr key={item.id}><Table.Td>{item.current_storage_gb} GB</Table.Td><Table.Td>{item.requested_storage_gb} GB</Table.Td><Table.Td>{dateLabel(item.created_at)}</Table.Td><Table.Td><Status value={item.status} /></Table.Td></Table.Tr>)}</Table.Tbody></Table> : <Text c="dimmed" ta="center" py="xl">No storage requests found.</Text>}</Loading>
    </Card></Grid.Col></Grid>
  </Container>;
}

export function SecurityAuditPage() {
  const [security, setSecurity] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const load = useCallback(async () => { setLoading(true); setLoadError(null); try {
    const [securityData, auditData] = await Promise.all([fetchSecurityStatus(), fetchSecurityAuditLogs()]);
    setSecurity(securityData); setLogs(records(auditData));
  } catch (error) { setLoadError(error); } finally { setLoading(false); } }, []);
  useEffect(() => { load(); }, [load]);
  return <Container size="xl"><PageHeader title="Security & Audit" subtitle="Review Sensitive-data encryption status and BADMS security activity." />
    <Alert color="violet" icon={<FaShieldAlt />} mb="md" variant="light">Sensitive archival must follow the IT Security review path and use AES-256 encryption. The UI displays server-reported status; encryption must be performed and verified by backend services.</Alert>
    <Loading active={loading}><Stack>
      <ErrorMessage error={loadError} fallback="Check the BADMS security and audit APIs." />
      <Grid>
        <Grid.Col span={{ base: 12, sm: 4 }}><Card withBorder p="lg"><Group><FaLock /><Text fw={600}>Encryption</Text></Group><Title order={3} mt="sm">{security?.encryption_enabled === true ? "Enabled" : security?.encryption_enabled === false ? "Disabled" : "Not reported"}</Title><Text size="sm" c="dimmed">Algorithm: {security?.algorithm || "AES-256 status not reported"}</Text></Card></Grid.Col>
        <Grid.Col span={{ base: 12, sm: 4 }}><Card withBorder p="lg"><Group><FaDatabase /><Text fw={600}>Sensitive records protected</Text></Group><Title order={3} mt="sm">{security?.protected_record_count ?? "—"}</Title><Text size="sm" c="dimmed">Reported by the security service</Text></Card></Grid.Col>
        <Grid.Col span={{ base: 12, sm: 4 }}><Card withBorder p="lg"><Group><FaCheckCircle /><Text fw={600}>Last verification</Text></Group><Title order={4} mt="sm">{dateLabel(security?.last_verified_at)}</Title><Text size="sm" c="dimmed">Latest server-reported check</Text></Card></Grid.Col>
      </Grid>
      <Card withBorder p="lg"><Group justify="space-between" mb="md"><Title order={4}>Security audit log</Title><Button variant="light" onClick={load}>Refresh</Button></Group>
        {logs.length ? <Table.ScrollContainer minWidth={760}><Table striped><Table.Thead><Table.Tr><Table.Th>Time</Table.Th><Table.Th>Actor</Table.Th><Table.Th>Action</Table.Th><Table.Th>Record / resource</Table.Th><Table.Th>Result</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{logs.map((item) => <Table.Tr key={item.id}><Table.Td>{dateLabel(item.created_at || item.timestamp)}</Table.Td><Table.Td>{item.actor_name || item.actor || "—"}</Table.Td><Table.Td>{item.action || "—"}</Table.Td><Table.Td>{item.resource_name || item.resource || "—"}</Table.Td><Table.Td><Status value={item.result || item.status} /></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer> : <Text c="dimmed" ta="center" py="xl">No security audit events available.</Text>}
      </Card>
    </Stack></Loading>
  </Container>;
}


export function FailureAlertsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const load = useCallback(async () => {
    setLoading(true); setLoadError(null);
    try { setItems(records(await fetchFailureAlerts())); }
    catch (error) { setLoadError(error); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return <Container size="xl"><PageHeader title="Backup Failure Alerts" subtitle="Review failed backup jobs, repeated failures and escalation status." />
    <Alert color="orange" icon={<FaExclamationTriangle />} mb="md" variant="light">Repeated backup failures should trigger the configured escalation and notification process. The escalation threshold and recipient are controlled by the backend.</Alert>
    <Card withBorder p="lg"><Group justify="space-between" mb="md"><Title order={4}>Failure and escalation history</Title><Button variant="light" onClick={load}><FaBell />&nbsp; Refresh</Button></Group>
      <ErrorMessage error={loadError} fallback="Check the BADMS failure-alert API." />
      <Loading active={loading}>{items.length ? <Table.ScrollContainer minWidth={760}><Table striped highlightOnHover><Table.Thead><Table.Tr><Table.Th>Database</Table.Th><Table.Th>Failure</Table.Th><Table.Th>Consecutive failures</Table.Th><Table.Th>Escalated to</Table.Th><Table.Th>Time</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{items.map((item) => <Table.Tr key={item.id}><Table.Td>{item.database_name || item.db_name || "—"}</Table.Td><Table.Td>{item.message || item.error_message || "Backup failed"}</Table.Td><Table.Td>{item.consecutive_failures ?? "—"}</Table.Td><Table.Td>{item.escalated_to || "—"}</Table.Td><Table.Td>{dateLabel(item.created_at || item.timestamp)}</Table.Td><Table.Td><Status value={item.status || (item.escalated ? "escalated" : "failed")} /></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer> : <Text c="dimmed" ta="center" py="xl">No backup failure alerts found.</Text>}</Loading>
    </Card>
  </Container>;
}
