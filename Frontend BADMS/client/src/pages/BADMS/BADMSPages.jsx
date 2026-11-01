/* eslint-disable react/prop-types */
import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  Alert,
  Badge,
  Button,
  Card,
  Center,
  Container,
  Grid,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { FaArchive, FaDatabase, FaLock, FaRedo, FaHdd } from "react-icons/fa";
import PageHeader from "../../components/PageHeader/PageHeader";
import {
  createArchiveRequest,
  createRestoreRequest,
  createStorageRequest,
  decideApproval,
  fetchApprovalQueue,
  fetchArchiveRequests,
  fetchRestoreRequests,
  fetchSecurityAuditLogs,
  fetchSecurityStatus,
  fetchStorageRequests,
} from "../../api/BADMS";
import { fetchBackups } from "../../api/Backups";

const unwrap = (value) => Array.isArray(value) ? value : value?.results || value?.items || [];
const showError = (error, fallback) => notifications.show({
  title: "Request failed",
  message: error.response?.data?.detail || error.response?.data?.message || fallback,
  color: "red",
});
const showSuccess = (message) => notifications.show({ title: "Success", message, color: "green" });
const statusColor = (status = "pending") => ({
  approved: "green", accepted: "green", completed: "green", rejected: "red",
  failed: "red", pending: "yellow", in_progress: "blue", "in progress": "blue",
}[String(status).toLowerCase()] || "gray");
const Status = ({ value }) => <Badge color={statusColor(value)} variant="light">{String(value || "unknown").replaceAll("_", " ")}</Badge>;
const dateText = (value) => value ? new Date(value).toLocaleString() : "—";
const Empty = ({ text = "No records found." }) => <Text c="dimmed" ta="center" py="xl">{text}</Text>;
const LoadState = ({ loading, children }) => loading ? <Center py="xl"><Loader /></Center> : children;

export function ArchiveRequestsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const form = useForm({
    initialValues: { database_name: "", archive_type: "full", data_classification: "internal", reason: "", retention_period_days: 365 },
    validate: {
      database_name: (v) => v.trim() ? null : "Enter a database name",
      reason: (v) => v.trim().length >= 10 ? null : "Explain the reason (at least 10 characters)",
      retention_period_days: (v) => Number(v) > 0 ? null : "Retention must be greater than zero",
    },
  });
  const load = useCallback(async () => {
    setLoading(true);
    try { setRows(unwrap(await fetchArchiveRequests())); }
    catch (error) { showError(error, "Could not load archive requests. Check that the BADMS API is available."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const submit = async (values) => {
    setSaving(true);
    try {
      await createArchiveRequest({ ...values, retention_period_days: Number(values.retention_period_days) });
      showSuccess("Archive request submitted for departmental review.");
      form.reset();
      load();
    } catch (error) { showError(error, "Could not submit archive request."); }
    finally { setSaving(false); }
  };
  return <Container size="xl">
    <PageHeader title="Archive Requests" subtitle="Submit and track secure database archival requests." />
    <Grid align="start">
      <Grid.Col span={{ base: 12, md: 5 }}>
        <Card withBorder radius="md" p="lg">
          <Group mb="md"><FaArchive /><Title order={4}>New archive request</Title></Group>
          <form onSubmit={form.onSubmit(submit)}>
            <Stack>
              <TextInput label="Database name" placeholder="e.g. student_records" required {...form.getInputProps("database_name")} />
              <Select label="Archive type" data={[{ value: "full", label: "Full archive" }, { value: "incremental", label: "Incremental archive" }]} {...form.getInputProps("archive_type")} />
              <Select label="Data classification" data={[{ value: "public", label: "Public" }, { value: "internal", label: "Internal" }, { value: "confidential", label: "Confidential" }, { value: "restricted", label: "Restricted" }]} {...form.getInputProps("data_classification")} />
              <NumberInput label="Retention period (days)" min={1} {...form.getInputProps("retention_period_days")} />
              <Textarea label="Business justification" minRows={3} placeholder="Why does this database need to be archived?" {...form.getInputProps("reason")} />
              <Alert color="blue" variant="light">Submission follows the BADMS approval workflow. Archival is not performed immediately.</Alert>
              <Button type="submit" loading={saving} leftSection={<FaArchive />}>Submit for approval</Button>
            </Stack>
          </form>
        </Card>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 7 }}>
        <Card withBorder radius="md" p="lg">
          <Group justify="space-between" mb="md"><Title order={4}>My archive requests</Title><Button variant="light" onClick={load}>Refresh</Button></Group>
          <LoadState loading={loading}>{rows.length ? <Table.ScrollContainer minWidth={650}><Table striped highlightOnHover>
            <Table.Thead><Table.Tr><Table.Th>Database</Table.Th><Table.Th>Type</Table.Th><Table.Th>Classification</Table.Th><Table.Th>Submitted</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{rows.map((row) => <Table.Tr key={row.id}><Table.Td>{row.database_name || row.db_name || "—"}</Table.Td><Table.Td>{row.archive_type || "—"}</Table.Td><Table.Td>{row.data_classification || "—"}</Table.Td><Table.Td>{dateText(row.created_at || row.submitted_at)}</Table.Td><Table.Td><Status value={row.status} /></Table.Td></Table.Tr>)}</Table.Tbody>
          </Table></Table.ScrollContainer> : <Empty text="No archive requests have been submitted." />}</LoadState>
        </Card>
      </Grid.Col>
    </Grid>
  </Container>;
}

export function RestoreRequestsPage() {
  const location = useLocation();
  const [backups, setBackups] = useState([]);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const form = useForm({ initialValues: { backup_id: "", target_database: "", reason: "" }, validate: {
    backup_id: (v) => v ? null : "Select a backup",
    target_database: (v) => v.trim() ? null : "Enter the target database",
    reason: (v) => v.trim().length >= 10 ? null : "Explain the reason (at least 10 characters)",
  } });
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [backupData, requestData] = await Promise.all([fetchBackups(), fetchRestoreRequests()]);
      setBackups(unwrap(backupData).filter((b) => b.status === "success"));
      setRows(unwrap(requestData));
    } catch (error) { showError(error, "Could not load backups or restoration requests."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (location.state?.backupId) form.setFieldValue("backup_id", String(location.state.backupId));
  }, [location.state, form]);
  const submit = async (values) => {
    setSaving(true);
    try {
      await createRestoreRequest(values);
      showSuccess("Restoration request submitted. It will run only after required approvals.");
      form.reset(); load();
    } catch (error) { showError(error, "Could not submit restoration request."); }
    finally { setSaving(false); }
  };
  return <Container size="xl">
    <PageHeader title="Restore Requests" subtitle="Request restoration from a successful backup and track its approval and execution." />
    <Grid align="start">
      <Grid.Col span={{ base: 12, md: 5 }}><Card withBorder p="lg" radius="md">
        <Group mb="md"><FaRedo /><Title order={4}>New restoration request</Title></Group>
        <form onSubmit={form.onSubmit(submit)}><Stack>
          <Select searchable label="Source backup" placeholder="Choose a successful backup" data={backups.map((b) => ({ value: String(b.id), label: `${b.db_name} · ${dateText(b.created_at)}` }))} {...form.getInputProps("backup_id")} />
          <TextInput label="Target database" placeholder="Database to restore into" {...form.getInputProps("target_database")} />
          <Textarea label="Reason for restoration" minRows={3} {...form.getInputProps("reason")} />
          <Alert color="orange" variant="light">This form creates an approval request. It does not directly restore or overwrite a database.</Alert>
          <Button type="submit" loading={saving} leftSection={<FaRedo />}>Submit restoration request</Button>
        </Stack></form>
      </Card></Grid.Col>
      <Grid.Col span={{ base: 12, md: 7 }}><Card withBorder p="lg" radius="md">
        <Group justify="space-between" mb="md"><Title order={4}>Restoration history</Title><Button variant="light" onClick={load}>Refresh</Button></Group>
        <LoadState loading={loading}>{rows.length ? <Table.ScrollContainer minWidth={620}><Table><Table.Thead><Table.Tr><Table.Th>Target DB</Table.Th><Table.Th>Backup</Table.Th><Table.Th>Requested</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{rows.map((r) => <Table.Tr key={r.id}><Table.Td>{r.target_database || r.db_name || "—"}</Table.Td><Table.Td>{r.backup_id || r.source_backup || "—"}</Table.Td><Table.Td>{dateText(r.created_at || r.submitted_at)}</Table.Td><Table.Td><Status value={r.status} /></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer> : <Empty text="No restoration requests found." />}</LoadState>
      </Card></Grid.Col>
    </Grid>
  </Container>;
}

export function ApprovalQueuePage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [decision, setDecision] = useState("approved");
  const [comments, setComments] = useState("");
  const [saving, setSaving] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try { setRows(unwrap(await fetchApprovalQueue("pending"))); }
    catch (error) { showError(error, "Could not load the approval queue."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  const submitDecision = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      await decideApproval(selected.id, decision, comments);
      showSuccess(`Request ${decision}.`); setSelected(null); setComments(""); load();
    } catch (error) { showError(error, "Could not record the approval decision."); }
    finally { setSaving(false); }
  };
  return <Container size="xl">
    <PageHeader title="Approval Queue" subtitle="Review BADMS archive, restore and storage requests assigned to your role." />
    <Card withBorder p="lg" radius="md">
      <Group justify="space-between" mb="md"><Title order={4}>Pending requests</Title><Button variant="light" onClick={load}>Refresh</Button></Group>
      <LoadState loading={loading}>{rows.length ? <Table.ScrollContainer minWidth={760}><Table highlightOnHover><Table.Thead><Table.Tr><Table.Th>Request</Table.Th><Table.Th>Type</Table.Th><Table.Th>Requested by</Table.Th><Table.Th>Department</Table.Th><Table.Th>Submitted</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{rows.map((r) => <Table.Tr key={r.id}><Table.Td>{r.title || r.database_name || r.db_name || `Request #${r.id}`}</Table.Td><Table.Td><Badge variant="light">{r.request_type || r.type || "—"}</Badge></Table.Td><Table.Td>{r.requested_by_name || r.requested_by || "—"}</Table.Td><Table.Td>{r.department || "—"}</Table.Td><Table.Td>{dateText(r.created_at || r.submitted_at)}</Table.Td><Table.Td><Button size="xs" onClick={() => setSelected(r)}>Review</Button></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer> : <Empty text="There are no pending approvals." />}</LoadState>
    </Card>
    <Modal opened={Boolean(selected)} onClose={() => setSelected(null)} title="Review request" centered>
      {selected && <Stack>
        <Text fw={600}>{selected.title || selected.database_name || selected.db_name || `Request #${selected.id}`}</Text>
        <Text size="sm" c="dimmed">{selected.description || selected.reason || "No additional description provided."}</Text>
        <Select label="Decision" data={[{ value: "approved", label: "Approve" }, { value: "rejected", label: "Reject" }]} value={decision} onChange={setDecision} />
        <Textarea label="Comments" value={comments} onChange={(e) => setComments(e.currentTarget.value)} placeholder="Add review comments" />
        <Group justify="flex-end"><Button variant="default" onClick={() => setSelected(null)}>Cancel</Button><Button color={decision === "approved" ? "green" : "red"} loading={saving} onClick={submitDecision}>{decision === "approved" ? "Approve request" : "Reject request"}</Button></Group>
      </Stack>}
    </Modal>
  </Container>;
}

export function StorageRequestsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const form = useForm({ initialValues: { current_storage_gb: 0, requested_storage_gb: 0, reason: "" }, validate: {
    requested_storage_gb: (v, values) => Number(v) > Number(values.current_storage_gb) ? null : "Requested capacity must exceed current capacity",
    reason: (v) => v.trim().length >= 10 ? null : "Provide a reason (at least 10 characters)",
  } });
  const load = useCallback(async () => { setLoading(true); try { setRows(unwrap(await fetchStorageRequests())); } catch (error) { showError(error, "Could not load storage requests."); } finally { setLoading(false); } }, []);
  useEffect(() => { load(); }, [load]);
  const submit = async (values) => { setSaving(true); try { await createStorageRequest({ ...values, current_storage_gb: Number(values.current_storage_gb), requested_storage_gb: Number(values.requested_storage_gb) }); showSuccess("Storage extension request submitted for approval."); form.reset(); load(); } catch (error) { showError(error, "Could not submit storage request."); } finally { setSaving(false); } };
  return <Container size="xl"><PageHeader title="Storage Extension" subtitle="Request additional storage capacity and monitor its approval status." />
    <Grid align="start"><Grid.Col span={{ base: 12, md: 5 }}><Card withBorder p="lg" radius="md"><Group mb="md"><FaHdd /><Title order={4}>New capacity request</Title></Group><form onSubmit={form.onSubmit(submit)}><Stack>
      <NumberInput label="Current capacity (GB)" min={0} {...form.getInputProps("current_storage_gb")} />
      <NumberInput label="Requested capacity (GB)" min={1} {...form.getInputProps("requested_storage_gb")} />
      <Textarea label="Justification" minRows={3} {...form.getInputProps("reason")} />
      <Button type="submit" loading={saving}>Submit storage request</Button>
    </Stack></form></Card></Grid.Col>
    <Grid.Col span={{ base: 12, md: 7 }}><Card withBorder p="lg" radius="md"><Group justify="space-between" mb="md"><Title order={4}>Request history</Title><Button variant="light" onClick={load}>Refresh</Button></Group><LoadState loading={loading}>{rows.length ? <Table><Table.Thead><Table.Tr><Table.Th>Current</Table.Th><Table.Th>Requested</Table.Th><Table.Th>Date</Table.Th><Table.Th>Status</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{rows.map((r) => <Table.Tr key={r.id}><Table.Td>{r.current_storage_gb ?? "—"} GB</Table.Td><Table.Td>{r.requested_storage_gb ?? "—"} GB</Table.Td><Table.Td>{dateText(r.created_at)}</Table.Td><Table.Td><Status value={r.status} /></Table.Td></Table.Tr>)}</Table.Tbody></Table> : <Empty text="No storage requests found." />}</LoadState></Card></Grid.Col></Grid>
  </Container>;
}

export function SecurityAuditPage() {
  const [security, setSecurity] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [status, audit] = await Promise.all([fetchSecurityStatus(), fetchSecurityAuditLogs()]);
      setSecurity(status); setLogs(unwrap(audit));
    } catch (error) { showError(error, "Could not load security status or audit logs."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);
  return <Container size="xl"><PageHeader title="Security & Audit" subtitle="Review encryption posture and security-sensitive BADMS activity." />
    <LoadState loading={loading}><Stack>
      <Grid>
        <Grid.Col span={{ base: 12, sm: 4 }}><Card withBorder p="lg"><Group><FaLock /><Text fw={600}>Encryption</Text></Group><Title order={3} mt="sm">{security?.encryption_enabled ? "Enabled" : security?.encryption_enabled === false ? "Disabled" : "Not reported"}</Title><Text size="sm" c="dimmed">Algorithm: {security?.algorithm || "Not reported by API"}</Text></Card></Grid.Col>
        <Grid.Col span={{ base: 12, sm: 4 }}><Card withBorder p="lg"><Group><FaDatabase /><Text fw={600}>Protected databases</Text></Group><Title order={3} mt="sm">{security?.protected_database_count ?? "—"}</Title><Text size="sm" c="dimmed">Reported by security service</Text></Card></Grid.Col>
        <Grid.Col span={{ base: 12, sm: 4 }}><Card withBorder p="lg"><Group><FaHdd /><Text fw={600}>Last security check</Text></Group><Title order={4} mt="sm">{dateText(security?.last_checked_at)}</Title><Text size="sm" c="dimmed">Latest reported verification</Text></Card></Grid.Col>
      </Grid>
      <Card withBorder p="lg"><Group justify="space-between" mb="md"><Title order={4}>Audit log</Title><Button variant="light" onClick={load}>Refresh</Button></Group>{logs.length ? <Table.ScrollContainer minWidth={760}><Table striped><Table.Thead><Table.Tr><Table.Th>Time</Table.Th><Table.Th>Actor</Table.Th><Table.Th>Action</Table.Th><Table.Th>Resource</Table.Th><Table.Th>Result</Table.Th></Table.Tr></Table.Thead><Table.Tbody>{logs.map((r) => <Table.Tr key={r.id}><Table.Td>{dateText(r.created_at || r.timestamp)}</Table.Td><Table.Td>{r.actor_name || r.actor || "—"}</Table.Td><Table.Td>{r.action || "—"}</Table.Td><Table.Td>{r.resource || r.resource_name || "—"}</Table.Td><Table.Td><Status value={r.result || r.status} /></Table.Td></Table.Tr>)}</Table.Tbody></Table></Table.ScrollContainer> : <Empty text="No audit events are available." />}</Card>
    </Stack></LoadState>
  </Container>;
}
