import { useState } from "react";
import {
  Badge, Button, Card, Container, FileInput, Group, NumberInput, Select,
  Stack, Table, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useArchiveClassification, useArchiveDecision, useArchives, useAuditEvents,
  useBackups, useBadmsReport, useConfigureEncryption, useCreateArchive,
  useCreateBackup, useCreateRestore, useCreateSchedule, useCreateSecurityPolicy,
  useCreateStorageExtension, useExecuteRestore, useRestoreDecision, useRestores,
  useSchedules, useSecurityPolicies, useStorageExtensionDecision,
  useStorageExtensions, useUpdateSchedule,
} from "../api/hooks";
import type {
  ArchiveRequest, AuditEvent, BackupSchedule, RestoreRequest,
  StorageExtension,
} from "../api/types";

function PageFrame({ title, subtitle, action, error, children }: {
  title: string;
  subtitle: string;
  action?: React.ReactNode;
  error?: unknown;
  children: React.ReactNode;
}) {
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title={title} subtitle={subtitle} action={action} />
      {children}
    </Container>
  );
}

function Status({ value }: { value: string }) {
  const color = value === "succeeded" || value === "archived"
    || value === "approved" || value === "restored" ? "green"
    : value === "failed" || value === "rejected" ? "red"
      : value === "running" || value === "security_review" ? "orange" : "gray";
  return <Badge color={color} variant="light">{value.replaceAll("_", " ")}</Badge>;
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <Text c="dimmed" ta="center" py="xl">
      {children}
    </Text>
  );
}

export function BackupsPage() {
  const { data = [], error, isPending } = useBackups();
  const { can } = useAuth();
  const [creating, setCreating] = useState(false);
  const [dataset, setDataset] = useState("fusion_integrated");
  const mutation = useCreateBackup();

  return (
    <PageFrame
      title="Backups"
      subtitle="Current database snapshot history and execution status"
      error={error}
      action={can("badms.backup.create") && (
        <Button onClick={() => setCreating(true)}>Run backup</Button>
      )}
    >
      <Card withBorder>
        {isPending ? <Text c="dimmed">Loading backups…</Text> : data.length === 0
          ? <Empty>No backup runs have been recorded.</Empty>
          : (
            <Table.ScrollContainer minWidth={720}>
              <Table striped highlightOnHover>
                <Table.Thead><Table.Tr>
                  <Table.Th>Dataset</Table.Th><Table.Th>Trigger</Table.Th>
                  <Table.Th>Status</Table.Th><Table.Th>Started</Table.Th>
                  <Table.Th>Size</Table.Th>
                </Table.Tr></Table.Thead>
                <Table.Tbody>
                  {data.map((run) => (
                    <Table.Tr key={run.id}>
                      <Table.Td>{run.dataset_key}</Table.Td>
                      <Table.Td>{run.trigger}</Table.Td>
                      <Table.Td><Status value={run.status} /></Table.Td>
                      <Table.Td>{run.started_at
                        ? new Date(run.started_at).toLocaleString() : "—"}</Table.Td>
                      <Table.Td>{run.size_bytes
                        ? `${(run.size_bytes / 1024 / 1024).toFixed(1)} MB` : "—"}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )}
      </Card>
      <FormModal
        opened={creating} onClose={() => setCreating(false)}
        title="Start a manual backup"
        subtitle="The result will appear in the backup history."
        submitting={mutation.isPending}
        disabled={!dataset.trim()}
        onSubmit={() => mutation.mutate(dataset, {
          onSuccess: () => {
            setCreating(false);
            notifications.show({ title: "Backup queued", message: "The worker will report its result." });
          },
          onError: (e) => notifications.show({
            color: "red", title: "Backup could not be queued",
            message: errorMessage(e),
          }),
        })}
      >
        <Select
          label="Dataset" data={[{ value: "fusion_integrated", label: "Fusion Integrated database" }]}
          value={dataset} onChange={(v) => setDataset(v ?? "")}
        />
      </FormModal>
    </PageFrame>
  );
}

export function SchedulesPage() {
  const { data = [], error, isPending } = useSchedules();
  const { can } = useAuth();
  const [creating, setCreating] = useState(false);
  const [scope, setScope] = useState<string | null>("local");
  const [cron, setCron] = useState("0 2 * * *");
  const [timezone, setTimezone] = useState("UTC");
  const create = useCreateSchedule();
  const update = useUpdateSchedule();
  const canCreate = can("badms.schedule.create");
  const canUpdate = can("badms.schedule.update");

  return (
    <PageFrame
      title="Backup schedules"
      subtitle="Local schedules override global defaults for the same dataset."
      error={error}
      action={canCreate && <Button onClick={() => setCreating(true)}>Add schedule</Button>}
    >
      <Card withBorder>
        {isPending ? <Text c="dimmed">Loading schedules…</Text> : data.length === 0
          ? <Empty>No schedules have been configured.</Empty>
          : (
            <Table.ScrollContainer minWidth={720}>
              <Table striped>
                <Table.Thead><Table.Tr>
                  <Table.Th>Scope</Table.Th><Table.Th>Dataset</Table.Th>
                  <Table.Th>Cron</Table.Th><Table.Th>Timezone</Table.Th>
                  <Table.Th>Enabled</Table.Th><Table.Th />
                </Table.Tr></Table.Thead>
                <Table.Tbody>
                  {data.map((row) => (
                    <Table.Tr key={row.id}>
                      <Table.Td>{row.scope}</Table.Td>
                      <Table.Td>{row.dataset_key}</Table.Td>
                      <Table.Td>{row.cron_expression}</Table.Td>
                      <Table.Td>{row.timezone}</Table.Td>
                      <Table.Td><Status value={row.enabled ? "enabled" : "disabled"} /></Table.Td>
                      <Table.Td>
                        {canUpdate && (
                          <Button size="xs" variant="subtle"
                            loading={update.isPending}
                            onClick={() => update.mutate(
                              { id: row.id, enabled: !row.enabled },
                              { onError: (e) => notifications.show({
                                color: "red", title: "Schedule update failed",
                                message: errorMessage(e),
                              }) },
                            )}>
                            {row.enabled ? "Disable" : "Enable"}
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )}
      </Card>
      <FormModal
        opened={creating} onClose={() => setCreating(false)}
        title="Create backup schedule" submitLabel="Save schedule"
        submitting={create.isPending}
        onSubmit={() => create.mutate({
          scope: scope as BackupSchedule["scope"],
          dataset_key: "fusion_integrated",
          cron_expression: cron,
          timezone,
          classification_filters: [],
          enabled: true,
        }, {
          onSuccess: () => setCreating(false),
          onError: (e) => notifications.show({
            color: "red", title: "Schedule could not be saved",
            message: errorMessage(e),
          }),
        })}
      >
        <Stack>
          <Select label="Scope" data={[
            { value: "local", label: "Local" }, { value: "global", label: "Global" },
          ]} value={scope} onChange={setScope} />
          <TextInput label="Five-field cron" value={cron} onChange={(e) => setCron(e.currentTarget.value)}
            description="Minute hour day month weekday" />
          <TextInput label="Timezone" value={timezone} onChange={(e) => setTimezone(e.currentTarget.value)} />
        </Stack>
      </FormModal>
    </PageFrame>
  );
}

export function ArchivesPage() {
  const { data = [], error, isPending } = useArchives();
  const { can, session } = useAuth();
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    file_name: "", data_date: "", owners: "", file_type: "",
    reason: "", initial_classification: "routine", attachment: null as File | null,
  });
  const [specialMode, setSpecialMode] = useState(false);
  const create = useCreateArchive();
  const special = useCreateArchive(true);
  const decision = useArchiveDecision();
  const classification = useArchiveClassification();
  const encryption = useConfigureEncryption();
  const canCreate = can("badms.archive.create");
  const isSuperAdmin = session?.active_role === "Super Admin";

  function submit(specialOperation: boolean) {
    const body = new FormData();
    Object.entries(form).forEach(([key, value]) => {
      if (value != null) body.append(key, value);
    });
    (specialOperation ? special : create).mutate(body, {
      onSuccess: () => {
        setCreating(false);
        notifications.show({ title: "Request submitted", message: "The archive is encrypted and queued for review." });
      },
      onError: (e) => notifications.show({
        color: "red", title: "Request was not submitted",
        message: errorMessage(e),
      }),
    });
  }

  return (
    <PageFrame
      title="Secure archives"
      subtitle="Submit, review, classify, and track encrypted archival requests."
      error={error}
      action={canCreate && (
        <Group>
          {isSuperAdmin && <Button variant="light" onClick={() => {
            setSpecialMode(true);
            setCreating(true);
          }}>
            Special archival
          </Button>}
          <Button onClick={() => {
            setSpecialMode(false);
            setCreating(true);
          }}>New request</Button>
        </Group>
      )}
    >
      <Card withBorder>
        {isPending ? <Text c="dimmed">Loading archival requests…</Text> : data.length === 0
          ? <Empty>No archival requests are visible to your role.</Empty>
          : (
            <Table.ScrollContainer minWidth={960}>
              <Table striped>
                <Table.Thead><Table.Tr>
                  <Table.Th>File</Table.Th><Table.Th>Department</Table.Th>
                  <Table.Th>Classification</Table.Th><Table.Th>Status</Table.Th>
                  <Table.Th>Submitted</Table.Th><Table.Th>Actions</Table.Th>
                </Table.Tr></Table.Thead>
                <Table.Tbody>
                  {data.map((row) => (
                    <ArchiveRow
                      key={row.id} row={row}
                      canReview={can("badms.archive.approve")}
                      canClassify={can("badms.archive.assign")}
                      canEncrypt={can("badms.encryption.manage")}
                      decision={decision} classification={classification}
                      encryption={encryption}
                    />
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )}
      </Card>
      <FormModal
        opened={creating} onClose={() => setCreating(false)}
        title={specialMode ? "Special archival" : "New archival request"}
        subtitle="Attachments are encrypted with AES-256-GCM and stored privately."
        submitLabel="Submit" submitting={create.isPending || special.isPending}
        disabled={!form.file_name || !form.data_date || !form.attachment}
        onSubmit={() => submit(specialMode)}
      >
        <Stack>
          <TextInput label="File name" required value={form.file_name}
            onChange={(e) => setForm({ ...form, file_name: e.currentTarget.value })} />
          <TextInput label="Data date" type="date" required value={form.data_date}
            onChange={(e) => setForm({ ...form, data_date: e.currentTarget.value })} />
          <TextInput label="Owners" required value={form.owners}
            onChange={(e) => setForm({ ...form, owners: e.currentTarget.value })} />
          <TextInput label="File type" required value={form.file_type}
            onChange={(e) => setForm({ ...form, file_type: e.currentTarget.value })} />
          <Select label="Initial classification" data={[
            { value: "routine", label: "Routine" },
            { value: "sensitive", label: "Sensitive" },
            { value: "critical", label: "Critical" },
            { value: "archival", label: "Archival" },
          ]} value={form.initial_classification}
          onChange={(v) => setForm({ ...form, initial_classification: v ?? "routine" })} />
          <Textarea label="Reason" required minRows={3} value={form.reason}
            onChange={(e) => setForm({ ...form, reason: e.currentTarget.value })} />
          <FileInput label="Attachment" required accept=".csv,.doc,.docx,.pdf,.txt,.xls,.xlsx"
            value={form.attachment}
            onChange={(attachment) => setForm({ ...form, attachment })} />
        </Stack>
      </FormModal>
    </PageFrame>
  );
}

function ArchiveRow({ row, canReview, canClassify, canEncrypt, decision,
  classification, encryption }: {
  row: ArchiveRequest;
  canReview: boolean;
  canClassify: boolean;
  canEncrypt: boolean;
  decision: ReturnType<typeof useArchiveDecision>;
  classification: ReturnType<typeof useArchiveClassification>;
  encryption: ReturnType<typeof useConfigureEncryption>;
}) {
  const actions: React.ReactNode[] = [];
  if (row.status === "submitted" && canReview) {
    actions.push(
      <Button key="approve" size="xs" onClick={() => decision.mutate(
        { id: row.id, approved: true },
      )}>Approve</Button>,
      <Button key="reject" size="xs" color="red" variant="light" onClick={() => decision.mutate(
        { id: row.id, approved: false },
      )}>Reject</Button>,
    );
  }
  if (row.status === "approved" && canClassify) {
    actions.push(
      <Select key="classify" size="xs" w={150} placeholder="Classify"
        data={["routine", "sensitive", "critical", "archival"]}
        onChange={(value) => value && classification.mutate({
          id: row.id, classification: value,
        })} />,
    );
  }
  if (row.status === "security_review" && canEncrypt) {
    actions.push(<Button key="encrypt" size="xs" onClick={() =>
      encryption.mutate(row.id)}>Confirm encryption</Button>);
  }
  return (
    <Table.Tr>
      <Table.Td>{row.file_name}</Table.Td>
      <Table.Td>{row.department_code || (row.special_operation ? "Special" : "—")}</Table.Td>
      <Table.Td>{row.classification || row.initial_classification}</Table.Td>
      <Table.Td><Status value={row.status} /></Table.Td>
      <Table.Td>{new Date(row.created_at).toLocaleString()}</Table.Td>
      <Table.Td><Group gap={4}>{actions}</Group></Table.Td>
    </Table.Tr>
  );
}

export function RestoresPage() {
  const { data = [], error, isPending } = useRestores();
  const { can } = useAuth();
  const [creating, setCreating] = useState(false);
  const [archive, setArchive] = useState("");
  const [reason, setReason] = useState("");
  const create = useCreateRestore();
  const decision = useRestoreDecision();
  const execute = useExecuteRestore();

  return (
    <PageFrame
      title="Restoration"
      subtitle="Request restoration of an archived file; Sensitive requests need SysAdmin approval."
      error={error}
      action={can("badms.restore.create") && (
        <Button onClick={() => setCreating(true)}>Request restore</Button>
      )}
    >
      <Card withBorder>
        {isPending ? <Text c="dimmed">Loading restoration requests…</Text> : data.length === 0
          ? <Empty>No restoration requests are visible to your role.</Empty>
          : (
            <Table.ScrollContainer minWidth={850}>
              <Table striped>
                <Table.Thead><Table.Tr>
                  <Table.Th>File</Table.Th><Table.Th>Class</Table.Th>
                  <Table.Th>Status</Table.Th><Table.Th>Reason</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr></Table.Thead>
                <Table.Tbody>
                  {data.map((row) => (
                    <RestoreRow key={row.id} row={row}
                      canApprove={can("badms.restore.approve")}
                      canExecute={can("badms.restore.restore")}
                      decision={decision} execute={execute} />
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )}
      </Card>
      <FormModal
        opened={creating} onClose={() => setCreating(false)}
        title="Request restoration" submitLabel="Submit request"
        submitting={create.isPending} disabled={!archive || !reason.trim()}
        onSubmit={() => create.mutate(
          { archive: Number(archive), reason },
          {
            onSuccess: () => setCreating(false),
            onError: (e) => notifications.show({
              color: "red", title: "Restore request failed",
              message: errorMessage(e),
            }),
          },
        )}
      >
        <Stack>
          <NumberInput label="Archive request ID" min={1} value={archive}
            onChange={(v) => setArchive(String(v ?? ""))} />
          <Textarea label="Reason" required value={reason} minRows={3}
            onChange={(e) => setReason(e.currentTarget.value)} />
        </Stack>
      </FormModal>
    </PageFrame>
  );
}

function RestoreRow({ row, canApprove, canExecute, decision, execute }: {
  row: RestoreRequest;
  canApprove: boolean;
  canExecute: boolean;
  decision: ReturnType<typeof useRestoreDecision>;
  execute: ReturnType<typeof useExecuteRestore>;
}) {
  return (
    <Table.Tr>
      <Table.Td>{row.file_name}</Table.Td>
      <Table.Td>{row.archive_classification}</Table.Td>
      <Table.Td><Status value={row.status} /></Table.Td>
      <Table.Td>{row.reason}</Table.Td>
      <Table.Td>
        <Group gap={4}>
          {canApprove && row.status === "submitted"
            && row.archive_classification === "sensitive" && (
              <>
                <Button size="xs" onClick={() => decision.mutate({
                  id: row.id, approved: true,
                })}>Approve</Button>
                <Button size="xs" color="red" variant="light"
                  onClick={() => decision.mutate({ id: row.id, approved: false })}>
                  Reject
                </Button>
              </>
          )}
          {canExecute && (row.status === "approved" || row.status === "submitted"
            || row.status === "restoring" || row.status === "restored") && (
              <Button size="xs" variant="light" loading={execute.isPending}
                onClick={() => execute.mutate(row.id, {
                  onError: (e) => notifications.show({
                    color: "red", title: "Restore failed",
                    message: errorMessage(e),
                  }),
                })}>
                Download
              </Button>
          )}
        </Group>
      </Table.Td>
    </Table.Tr>
  );
}

export function StorageExtensionsPage() {
  const { data = [], error, isPending } = useStorageExtensions();
  const { can } = useAuth();
  const [creating, setCreating] = useState(false);
  const [bytes, setBytes] = useState<number | string>("");
  const [justification, setJustification] = useState("");
  const create = useCreateStorageExtension();
  const decision = useStorageExtensionDecision();

  return (
    <PageFrame
      title="Storage extensions"
      subtitle="Requests are available only at quota and are decided by the requester's HoD."
      error={error}
      action={can("badms.storage_extension.create") && (
        <Button onClick={() => setCreating(true)}>Request capacity</Button>
      )}
    >
      <Card withBorder>
        {isPending ? <Text c="dimmed">Loading storage requests…</Text> : data.length === 0
          ? <Empty>No storage-extension requests are visible to your role.</Empty>
          : (
            <Table.ScrollContainer minWidth={800}>
              <Table striped>
                <Table.Thead><Table.Tr>
                  <Table.Th>Requested</Table.Th><Table.Th>Quota</Table.Th>
                  <Table.Th>Additional</Table.Th><Table.Th>Status</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr></Table.Thead>
                <Table.Tbody>
                  {data.map((row) => (
                    <ExtensionRow key={row.id} row={row}
                      canDecide={can("badms.storage_extension.approve")}
                      decision={decision} />
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          )}
      </Card>
      <FormModal
        opened={creating} onClose={() => setCreating(false)}
        title="Request storage extension" submitLabel="Submit"
        submitting={create.isPending}
        disabled={!Number(bytes) || !justification.trim()}
        onSubmit={() => create.mutate(
          { requested_bytes: Number(bytes), justification },
          {
            onSuccess: () => setCreating(false),
            onError: (e) => notifications.show({
              color: "red", title: "Capacity request failed",
              message: errorMessage(e),
            }),
          },
        )}
      >
        <Stack>
          <NumberInput label="Additional bytes" min={1} value={bytes}
            onChange={setBytes} />
          <Textarea label="Justification" required value={justification}
            onChange={(e) => setJustification(e.currentTarget.value)} minRows={3} />
        </Stack>
      </FormModal>
    </PageFrame>
  );
}

function ExtensionRow({ row, canDecide, decision }: {
  row: StorageExtension;
  canDecide: boolean;
  decision: ReturnType<typeof useStorageExtensionDecision>;
}) {
  return (
    <Table.Tr>
      <Table.Td>{row.current_usage_bytes.toLocaleString()} bytes</Table.Td>
      <Table.Td>{row.quota_bytes.toLocaleString()} bytes</Table.Td>
      <Table.Td>{row.requested_bytes.toLocaleString()} bytes</Table.Td>
      <Table.Td><Status value={row.status} /></Table.Td>
      <Table.Td>
        {canDecide && row.status === "submitted" && (
          <Group gap={4}>
            <Button size="xs" onClick={() => decision.mutate({
              id: row.id, approved: true,
            })}>Approve</Button>
            <Button size="xs" color="red" variant="light"
              onClick={() => decision.mutate({ id: row.id, approved: false })}>
              Reject
            </Button>
          </Group>
        )}
      </Table.Td>
    </Table.Tr>
  );
}

export function AuditPage() {
  const { data = [], error, isPending } = useAuditEvents();
  return (
    <PageFrame title="Audit history" subtitle="Append-only BADMS operations and outcomes."
      error={error}>
      <Card withBorder>
        {isPending ? <Text c="dimmed">Loading audit history…</Text> : data.length === 0
          ? <Empty>No audit events are visible to your role.</Empty>
          : <Table.ScrollContainer minWidth={780}><Table striped>
            <Table.Thead><Table.Tr>
              <Table.Th>Time</Table.Th><Table.Th>Action</Table.Th>
              <Table.Th>Resource</Table.Th><Table.Th>Outcome</Table.Th>
            </Table.Tr></Table.Thead>
            <Table.Tbody>{data.map((row: AuditEvent) => (
              <Table.Tr key={row.id}>
                <Table.Td>{new Date(row.occurred_at).toLocaleString()}</Table.Td>
                <Table.Td>{row.action}</Table.Td>
                <Table.Td>{row.resource} {row.resource_id}</Table.Td>
                <Table.Td><Status value={row.outcome} /></Table.Td>
              </Table.Tr>
            ))}</Table.Tbody>
          </Table></Table.ScrollContainer>}
      </Card>
    </PageFrame>
  );
}

export function ReportsPage() {
  const { data, error, isPending } = useBadmsReport();
  return (
    <PageFrame title="BADMS reports" subtitle="Role-scoped operational status counts."
      error={error}>
      <Card withBorder>
        {isPending ? <Text c="dimmed">Loading report…</Text> : !data
          ? <Empty>No report data is available.</Empty>
          : <Stack>
            <Text size="xs" c="dimmed">
              Generated {new Date(data.generated_at).toLocaleString()}
            </Text>
            {Object.entries({
              "Backups": data.backups_by_status,
              "Archives": data.archives_by_status,
              "Storage requests": data.storage_extensions_by_status,
            }).map(([label, counts]) => (
              <Card key={label} withBorder>
                <Text fw={600} mb="xs">{label}</Text>
                <Group>{Object.entries(counts).map(([state, count]) => (
                  <Badge key={state} variant="light">
                    {state.replaceAll("_", " ")}: {count}
                  </Badge>
                ))}</Group>
              </Card>
            ))}
          </Stack>}
      </Card>
    </PageFrame>
  );
}

export function SecurityPoliciesPage() {
  const { data = [], error, isPending } = useSecurityPolicies();
  const { can } = useAuth();
  const [creating, setCreating] = useState(false);
  const [classification, setClassification] = useState<string | null>("sensitive");
  const [retention, setRetention] = useState<number | string>("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [encryptionRequired, setEncryptionRequired] = useState("true");
  const create = useCreateSecurityPolicy();

  return (
    <PageFrame
      title="Security policies"
      subtitle="Effective-dated classification, encryption, and retention requirements."
      error={error}
      action={can("badms.security_policy.manage") && (
        <Button onClick={() => setCreating(true)}>Add policy version</Button>
      )}
    >
      <Card withBorder>
        {isPending ? <Text c="dimmed">Loading security policies…</Text> : data.length === 0
          ? <Empty>No policy versions are configured.</Empty>
          : <Table.ScrollContainer minWidth={720}><Table striped>
            <Table.Thead><Table.Tr>
              <Table.Th>Classification</Table.Th><Table.Th>Effective from</Table.Th>
              <Table.Th>Retention</Table.Th><Table.Th>Encryption</Table.Th>
            </Table.Tr></Table.Thead>
            <Table.Tbody>{data.map((row) => (
              <Table.Tr key={row.id}>
                <Table.Td>{row.classification}</Table.Td>
                <Table.Td>{new Date(row.effective_from).toLocaleString()}</Table.Td>
                <Table.Td>{row.retention_days ?? "Not specified"}</Table.Td>
                <Table.Td>{row.encryption_required ? "Required" : "Not required"}</Table.Td>
              </Table.Tr>
            ))}</Table.Tbody>
          </Table></Table.ScrollContainer>}
      </Card>
      <FormModal
        opened={creating} onClose={() => setCreating(false)}
        title="Create security policy version"
        submitting={create.isPending}
        disabled={!classification || !effectiveFrom}
        onSubmit={() => create.mutate({
          classification: classification ?? undefined,
          retention_days: retention === "" ? null : Number(retention),
          effective_from: new Date(effectiveFrom).toISOString(),
          encryption_required: encryptionRequired === "true",
        }, {
          onSuccess: () => setCreating(false),
          onError: (e) => notifications.show({
            color: "red", title: "Policy was not saved",
            message: errorMessage(e),
          }),
        })}
      >
        <Stack>
          <Select label="Classification" data={[
            "critical", "sensitive", "routine", "archival",
          ]} value={classification} onChange={setClassification} />
          <TextInput label="Effective from" type="datetime-local"
            value={effectiveFrom} onChange={(e) => setEffectiveFrom(e.currentTarget.value)} />
          <NumberInput label="Retention days (leave empty if not set)"
            min={1} value={retention} onChange={setRetention} />
          <Select label="Encryption required" data={[
            { value: "true", label: "Yes" }, { value: "false", label: "No" },
          ]} value={encryptionRequired} onChange={(v) => setEncryptionRequired(v ?? "true")} />
        </Stack>
      </FormModal>
    </PageFrame>
  );
}
