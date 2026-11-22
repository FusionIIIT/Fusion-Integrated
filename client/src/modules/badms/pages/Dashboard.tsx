import { useEffect, useState, type FormEvent } from "react";
import {
  Alert, Badge, Button, Card, FileInput, Group, Select, SimpleGrid, Stack,
  Table, Text, TextInput, Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import {
  classifyArchive, completeSensitiveArchive, decideArchive, getArchives, getAudit, getBackups,
  runBackup, submitArchive, type ArchiveRequest, type AuditEvent, type BackupRun,
} from "../api/client";

const classOptions = ["ROUTINE", "CRITICAL", "SENSITIVE", "ARCHIVAL"]
  .map((value) => ({ value, label: value[0] + value.slice(1).toLowerCase() }));

export default function BadmsDashboard() {
  const { can } = useAuth();
  const [backups, setBackups] = useState<BackupRun[]>([]);
  const [archives, setArchives] = useState<ArchiveRequest[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [dataDate, setDataDate] = useState("");
  const [owners, setOwners] = useState("");
  const [fileType, setFileType] = useState("");
  const [reason, setReason] = useState("");
  const [classification, setClassification] = useState("ROUTINE");
  const [file, setFile] = useState<File | null>(null);

  async function refresh() {
    setError("");
    try {
      const results = await Promise.all([
        can("badms.backup.view") ? getBackups() : Promise.resolve([]),
        getArchives(),
        can("badms.audit.view") ? getAudit() : Promise.resolve([]),
      ]);
      setBackups(results[0]); setArchives(results[1]); setAudit(results[2]);
    } catch (err) { setError(errorMessage(err)); }
  }
  useEffect(() => { void refresh(); }, []);

  async function triggerBackup() {
    setBusy(true);
    try {
      const result = await runBackup();
      notifications.show({ color: result.status === "SUCCESS" ? "teal" : "red",
        title: result.status === "SUCCESS" ? "Backup completed" : "Backup failed",
        message: result.message });
      await refresh();
    } catch (err) { notifications.show({ color: "red", title: "Backup failed", message: errorMessage(err) }); }
    finally { setBusy(false); }
  }

  async function createRequest(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    const payload = new FormData();
    payload.append("file_name", name); payload.append("data_date", dataDate);
    payload.append("owners", owners); payload.append("file_type", fileType);
    payload.append("reason", reason); payload.append("initial_classification", classification);
    payload.append("attachment", file);
    setBusy(true);
    try {
      await submitArchive(payload);
      notifications.show({ color: "teal", title: "Request submitted", message: "Your request is now awaiting review." });
      setName(""); setOwners(""); setFileType(""); setReason(""); setFile(null);
      await refresh();
    } catch (err) { notifications.show({ color: "red", title: "Could not submit request", message: errorMessage(err) }); }
    finally { setBusy(false); }
  }

  async function review(id: number, action: "approve" | "reject") {
    try { await decideArchive(id, action); await refresh(); }
    catch (err) { notifications.show({ color: "red", title: "Decision failed", message: errorMessage(err) }); }
  }
  async function classify(id: number, value: string) {
    try { await classifyArchive(id, value); await refresh(); }
    catch (err) { notifications.show({ color: "red", title: "Classification failed", message: errorMessage(err) }); }
  }
  async function completeSensitive(id: number) {
    try { await completeSensitiveArchive(id); await refresh(); }
    catch (err) { notifications.show({ color: "red", title: "Archive completion failed", message: errorMessage(err) }); }
  }

  const counts = {
    successful: backups.filter((b) => b.status === "SUCCESS").length,
    failed: backups.filter((b) => b.status === "FAILED").length,
    pending: archives.filter((a) => ["SUBMITTED", "HOD_APPROVED", "SECURITY_REVIEW"].includes(a.status)).length,
  };
  return (
    <Stack maw={1200} mx="auto" p="md" gap="lg">
      <div><Title order={2}>Backup &amp; Database Archives</Title>
        <Text c="dimmed" mt={4}>Create database snapshots and track secure archival requests.</Text></div>
      {error && <Alert color="red" title="Could not load BADMS">{error}</Alert>}
      <SimpleGrid cols={{ base: 1, sm: 3 }}>
        <Card withBorder><Text size="sm" c="dimmed">Successful backups</Text><Title order={3}>{counts.successful}</Title></Card>
        <Card withBorder><Text size="sm" c="dimmed">Failed backups</Text><Title order={3}>{counts.failed}</Title></Card>
        <Card withBorder><Text size="sm" c="dimmed">Active archive requests</Text><Title order={3}>{counts.pending}</Title></Card>
      </SimpleGrid>
      {can("badms.backup.run") && <Card withBorder>
        <Group justify="space-between"><div><Text fw={600}>Database backup</Text>
          <Text size="sm" c="dimmed">Create a compressed current-state database snapshot with a SHA-256 checksum.</Text></div>
          <Button loading={busy} onClick={() => void triggerBackup()}>Run backup</Button></Group>
      </Card>}
      {can("badms.archive.submit") && <Card withBorder>
        <Text fw={600} mb="sm">Submit secure archival request</Text>
        <form onSubmit={(e) => void createRequest(e)}><Stack>
          <TextInput label="Data or file name" value={name} onChange={(e) => setName(e.currentTarget.value)} required />
          <SimpleGrid cols={{ base: 1, sm: 2 }}>
            <TextInput label="Data date" type="date" value={dataDate} onChange={(e) => setDataDate(e.currentTarget.value)} required />
            <TextInput label="Owners" value={owners} onChange={(e) => setOwners(e.currentTarget.value)} required />
            <TextInput label="File type" value={fileType} onChange={(e) => setFileType(e.currentTarget.value)} required />
            <Select label="Initial classification" data={classOptions} value={classification} onChange={(v) => setClassification(v ?? "ROUTINE")} />
          </SimpleGrid>
          <Textarea label="Reason for archival" value={reason} onChange={(e) => setReason(e.currentTarget.value)} required />
          <FileInput label="Attachment" value={file} onChange={setFile} required />
          <Button type="submit" loading={busy} w="fit-content">Submit request</Button>
        </Stack></form>
      </Card>}
      <Card withBorder>
        <Text fw={600} mb="sm">Archival requests</Text>
        {archives.length === 0 ? <Text c="dimmed" size="sm">No requests to display.</Text> :
          <Table.ScrollContainer minWidth={760}><Table striped highlightOnHover>
            <Table.Thead><Table.Tr><Table.Th>Name</Table.Th><Table.Th>Submitted</Table.Th><Table.Th>Classification</Table.Th><Table.Th>Status</Table.Th><Table.Th>Action</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{archives.map((item: ArchiveRequest) => <Table.Tr key={item.id}>
              <Table.Td><Text fw={500}>{item.file_name}</Text><Text size="xs" c="dimmed">{item.file_type} · {item.department || "No department"}</Text><a href={`/api/v1/badms/archives/${item.id}/attachment/`}>Open attachment</a></Table.Td>
              <Table.Td>{new Date(item.created_at).toLocaleDateString()}</Table.Td>
              <Table.Td>{item.classification}</Table.Td>
              <Table.Td><Badge variant="light">{item.status.replaceAll("_", " ")}</Badge></Table.Td>
              <Table.Td>{can("badms.archive.review") && item.status === "SUBMITTED" ? <Group gap="xs">
                <Button size="xs" onClick={() => void review(item.id, "approve")}>Approve</Button>
                <Button size="xs" color="red" variant="light" onClick={() => void review(item.id, "reject")}>Reject</Button>
              </Group> : can("badms.archive.classify") && item.status === "HOD_APPROVED" ?
                <Select aria-label="Authoritative classification" data={classOptions} defaultValue={item.initial_classification}
                  onChange={(v) => v && void classify(item.id, v)} /> : can("badms.archive.secure") && item.status === "SECURITY_REVIEW" ?
                <Button size="xs" onClick={() => void completeSensitive(item.id)}>Complete encrypted archive</Button> : <Text size="sm" c="dimmed">—</Text>}</Table.Td>
            </Table.Tr>)}</Table.Tbody>
          </Table></Table.ScrollContainer>}
      </Card>
      {can("badms.backup.view") && <Card withBorder>
        <Text fw={600} mb="sm">Backup history</Text>
        {backups.length === 0 ? <Text c="dimmed" size="sm">No backups recorded yet.</Text> :
          <Table.ScrollContainer minWidth={650}><Table><Table.Thead><Table.Tr><Table.Th>Started</Table.Th><Table.Th>Status</Table.Th><Table.Th>Size</Table.Th><Table.Th>Checksum</Table.Th><Table.Th>Artifact</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{backups.map((run) => <Table.Tr key={run.id}><Table.Td>{new Date(run.started_at).toLocaleString()}</Table.Td><Table.Td><Badge color={run.status === "SUCCESS" ? "teal" : run.status === "FAILED" ? "red" : "yellow"}>{run.status}</Badge></Table.Td><Table.Td>{run.size_bytes.toLocaleString()} bytes</Table.Td><Table.Td><Text size="xs" ff="monospace">{run.checksum.slice(0, 16)}{run.checksum ? "…" : "—"}</Text></Table.Td><Table.Td>{run.artifact_url ? <a href={run.artifact_url}>Download</a> : "—"}</Table.Td></Table.Tr>)}</Table.Tbody>
          </Table></Table.ScrollContainer>}
      </Card>}
      {can("badms.audit.view") && <Card withBorder>
        <Text fw={600} mb="sm">Recent activity</Text>
        {audit.length === 0 ? <Text c="dimmed" size="sm">No activity recorded.</Text> : audit.slice(0, 12).map((event) =>
          <Group key={event.id} justify="space-between" py={6} style={{ borderBottom: "1px solid var(--mantine-color-gray-2)" }}>
            <div><Text size="sm">{event.action.replaceAll(".", " ")}</Text><Text size="xs" c="dimmed">{event.object_type} {event.object_id}</Text></div>
            <Text size="xs" c="dimmed">{new Date(event.created_at).toLocaleString()}</Text>
          </Group>)}
      </Card>}
    </Stack>
  );
}
