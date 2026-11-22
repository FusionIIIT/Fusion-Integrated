import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Card, Container, Group, NumberInput, Stack, Text, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage, http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

type Row = { id: number; status: string; requested_bytes?: number;
  archive_request_id?: number; file_name?: string; justification?: string };
type Page<T> = { results: T[] };
type Schedule = { id: number; scope: string; dataset: string; frequency: string;
  scheduled_time: string; timezone: string; enabled: boolean };
type AuditRow = { id: number; action: string; outcome: string; object_type: string;
  object_id: string; created_at: string };

function useRefresh() {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: ["badms"] });
}

export default function OperationsPage() {
  const { can } = useAuth();
  const refresh = useRefresh();
  const [archiveId, setArchiveId] = useState<number | string>("");
  const [extensionBytes, setExtensionBytes] = useState<number | string>("");
  const [justification, setJustification] = useState("");
  const [dataset, setDataset] = useState("");
  const [specialRef, setSpecialRef] = useState("");
  const [specialDescription, setSpecialDescription] = useState("");
  const [specialFile, setSpecialFile] = useState<File | null>(null);
  const canRestore = can("badms.restore.create") || can("badms.restore.view_self") ||
    can("badms.restore.execute");
  const canStorage = can("badms.storage_extension.create") ||
    can("badms.storage_extension.review_department");
  const restores = useQuery({
    queryKey: ["badms", "restorations"], enabled: canRestore,
    queryFn: async () => (await http.get<Page<Row>>("/badms/restoration_requests")).data,
  });
  const extensions = useQuery({
    queryKey: ["badms", "storage-extensions"], enabled: canStorage,
    queryFn: async () => (await http.get<Page<Row>>("/badms/storage_extension_requests")).data,
  });
  const canManageSchedules = can("badms.schedule_local.manage") ||
    can("badms.schedule_global.manage");
  const schedules = useQuery({
    queryKey: ["badms", "schedules"], enabled: canManageSchedules,
    queryFn: async () => (await http.get<Page<Schedule>>("/badms/schedules")).data,
  });
  const canAudit = can("badms.audit.view") || can("badms.security.audit") ||
    can("badms.reports.department");
  const audit = useQuery({
    queryKey: ["badms", "audit"], enabled: canAudit,
    queryFn: async () => (await http.get<Page<AuditRow>>("/badms/audit_events")).data,
  });
  const departmentReport = useQuery({
    queryKey: ["badms", "department-report"], enabled: can("badms.reports.department"),
    queryFn: async () => (await http.get<Record<string, number | string>>(
      "/badms/reports/department")).data,
  });
  const securityReport = useQuery({
    queryKey: ["badms", "security-report"], enabled: can("badms.security.audit"),
    queryFn: async () => (await http.get<{ events: { action: string; outcome: string;
      total: number }[] }>("/badms/reports/security")).data,
  });
  const myThreshold = useQuery({
    queryKey: ["badms", "my-threshold"], enabled: can("badms.storage_extension.create"),
    queryFn: async () => (await http.get<{ usage_bytes: number; quota_bytes: number | null;
      is_full: boolean }>("/badms/storage_thresholds/me")).data,
  });
  const createRestore = useMutation({
    mutationFn: async () => (await http.post("/badms/restoration_requests", {
      archive_request_id: Number(archiveId),
    })).data,
    onSuccess: () => { refresh(); setArchiveId(""); },
  });
  const createExtension = useMutation({
    mutationFn: async () => (await http.post("/badms/storage_extension_requests", {
      requested_bytes: Number(extensionBytes), justification,
    })).data,
    onSuccess: () => { refresh(); setExtensionBytes(""); setJustification(""); },
  });
  const createSchedule = useMutation({
    mutationFn: async () => (await http.post<Schedule>("/badms/schedules", {
      scope: can("badms.schedule_global.manage") ? "global" : "local",
      dataset, frequency: "daily", scheduled_time: "02:00", timezone: "Asia/Kolkata",
      classifications: [], enabled: true,
    })).data,
    onSuccess: () => { refresh(); setDataset(""); },
  });
  const toggleSchedule = useMutation({
    mutationFn: async (schedule: Schedule) => (await http.patch<Schedule>(
      `/badms/schedules/${schedule.id}`, { enabled: !schedule.enabled })).data,
    onSuccess: refresh,
  });
  const createSpecialArchive = useMutation({
    mutationFn: async () => {
      const form = new FormData();
      if (specialFile) form.set("attachment", specialFile);
      form.set("offline_request_reference", specialRef);
      form.set("research_description", specialDescription);
      return (await http.post("/badms/special_archives", form, {
        headers: { "Content-Type": "multipart/form-data" },
      })).data;
    },
    onSuccess: () => { refresh(); setSpecialFile(null); setSpecialRef(""); setSpecialDescription(""); },
  });
  const transition = useMutation({
    mutationFn: async ({ kind, id, action }: { kind: "restoration" | "storage";
      id: number; action: "approve" | "reject" | "restore" }) => {
      const path = kind === "storage" ? `/badms/storage_extension_requests/${id}/decision`
        : action === "restore" ? `/badms/restoration_requests/${id}/execution`
          : `/badms/restoration_requests/${id}/decision`;
      return (await http.post(path, action === "restore" ? {} : { decision: action })).data;
    },
    onSuccess: refresh,
  });

  function reportError(title: string, error: unknown) {
    notifications.show({ title, message: errorMessage(error), color: "red" });
  }

  return (
    <Container size="lg">
      <PageHeader title="Recovery and reports"
        subtitle="Request archive recovery and additional storage; review requests in your role." />
      <Stack>
        {can("badms.restore.create") && <Card withBorder padding="lg">
          <form onSubmit={(event) => {
            event.preventDefault();
            createRestore.mutate(undefined, { onError: (error) => reportError("Could not request restoration", error) });
          }}>
            <Stack>
              <Text fw={700}>Request restoration</Text>
              <NumberInput label="Archive request ID" min={1} value={archiveId}
                onChange={setArchiveId} required />
              <Button type="submit" loading={createRestore.isPending}>Request restoration</Button>
            </Stack>
          </form>
        </Card>}
        {can("badms.storage_extension.create") && <Card withBorder padding="lg">
          <form onSubmit={(event) => {
            event.preventDefault();
            createExtension.mutate(undefined, { onError: (error) => reportError("Could not request storage", error) });
          }}>
            <Stack>
              <Text fw={700}>Request additional storage</Text>
              <NumberInput label="Additional bytes" min={1} value={extensionBytes}
                onChange={setExtensionBytes} required />
              <TextInput label="Justification" value={justification}
                onChange={(event) => setJustification(event.currentTarget.value)} required />
              <Button type="submit" loading={createExtension.isPending}>Submit storage request</Button>
            </Stack>
          </form>
        </Card>}
        {canRestore && <Card withBorder padding="lg">
          <Stack>
            <Text fw={700}>Restoration requests</Text>
            {(restores.data?.results ?? []).map((row) => <Group key={row.id} justify="space-between">
              <Text>Request #{row.id} · archive #{row.archive_request_id} · {row.status}</Text>
              {can("badms.restore.approve") && row.status === "Sensitive Restoration Pending Approval" && <Group>
                <Button onClick={() => transition.mutate({ kind: "restoration", id: row.id, action: "approve" },
                  { onError: (error) => reportError("Could not approve restoration", error) })}>Approve</Button>
                <Button color="red" variant="light" onClick={() => transition.mutate({ kind: "restoration", id: row.id, action: "reject" },
                  { onError: (error) => reportError("Could not reject restoration", error) })}>Reject</Button>
              </Group>}
              {can("badms.restore.execute") && row.status === "Approved for Restoration" &&
                <Button onClick={() => transition.mutate({ kind: "restoration", id: row.id, action: "restore" },
                  { onError: (error) => reportError("Could not restore archive", error) })}>Restore</Button>}
            </Group>)}
            {!restores.isPending && !restores.data?.results.length && <Text c="dimmed">No restoration requests.</Text>}
          </Stack>
        </Card>}
        {canStorage && <Card withBorder padding="lg">
          <Stack>
            <Text fw={700}>Storage extension requests</Text>
            {(extensions.data?.results ?? []).map((row) => <Group key={row.id} justify="space-between">
              <Text>Request #{row.id} · {row.requested_bytes} bytes · {row.status}</Text>
              {can("badms.storage_extension.review_department") && row.status === "Submitted" && <Group>
                <Button onClick={() => transition.mutate({ kind: "storage", id: row.id, action: "approve" },
                  { onError: (error) => reportError("Could not approve storage", error) })}>Approve</Button>
                <Button color="red" variant="light" onClick={() => transition.mutate({ kind: "storage", id: row.id, action: "reject" },
                  { onError: (error) => reportError("Could not reject storage", error) })}>Reject</Button>
              </Group>}
            </Group>)}
            {!extensions.isPending && !extensions.data?.results.length && <Text c="dimmed">No storage requests.</Text>}
          </Stack>
        </Card>}
        {can("badms.storage_extension.create") && myThreshold.data && <Card withBorder padding="lg">
          <Text fw={700}>Your storage use</Text>
          <Text>{myThreshold.data.usage_bytes} bytes used of {myThreshold.data.quota_bytes ?? "institute quota not configured"}
            {myThreshold.data.is_full ? " · quota full" : ""}</Text>
        </Card>}
        {canManageSchedules && <Card withBorder padding="lg">
          <Stack>
            <Text fw={700}>Backup schedules</Text>
            {(schedules.data?.results ?? []).map((schedule) => <Group key={schedule.id} justify="space-between">
              <Text>{schedule.scope} · {schedule.dataset} · {schedule.frequency} at {schedule.scheduled_time} {schedule.timezone}
                {schedule.enabled ? " · enabled" : " · disabled"}</Text>
              <Button variant="light" onClick={() => toggleSchedule.mutate(schedule, {
                onError: (error) => reportError("Could not update schedule", error),
              })}>{schedule.enabled ? "Pause" : "Enable"}</Button>
            </Group>)}
            <form onSubmit={(event) => {
              event.preventDefault();
              createSchedule.mutate(undefined, { onError: (error) => reportError("Could not save schedule", error) });
            }}><Group align="end"><TextInput label="Dataset name" value={dataset}
              onChange={(event) => setDataset(event.currentTarget.value)} required />
              <Button type="submit" loading={createSchedule.isPending}>Add daily schedule</Button></Group></form>
          </Stack>
        </Card>}
        {can("badms.archive.special") && <Card withBorder padding="lg">
          <form onSubmit={(event) => {
            event.preventDefault();
            createSpecialArchive.mutate(undefined, { onError: (error) => reportError("Could not archive research data", error) });
          }}><Stack><Text fw={700}>Special research archive</Text>
            <TextInput label="Offline request reference" value={specialRef}
              onChange={(event) => setSpecialRef(event.currentTarget.value)} required />
            <TextInput label="Research description" value={specialDescription}
              onChange={(event) => setSpecialDescription(event.currentTarget.value)} required />
            <input aria-label="Special archive file" type="file" required
              onChange={(event) => setSpecialFile(event.currentTarget.files?.[0] ?? null)} />
            <Button type="submit" loading={createSpecialArchive.isPending}
              disabled={!specialFile}>Submit special archive</Button>
          </Stack></form>
        </Card>}
        {canAudit && <Card withBorder padding="lg"><Stack>
          <Text fw={700}>Audit history</Text>
          {(audit.data?.results ?? []).map((event) => <Text key={event.id}>
            {event.created_at} · {event.action} · {event.object_type} #{event.object_id} · {event.outcome}
          </Text>)}
        </Stack></Card>}
        {departmentReport.data && <Card withBorder padding="lg"><Stack>
          <Text fw={700}>Department report</Text>
          <Text>{JSON.stringify(departmentReport.data)}</Text>
        </Stack></Card>}
        {securityReport.data && <Card withBorder padding="lg"><Stack>
          <Text fw={700}>Security report</Text>
          {securityReport.data.events.map((event, index) => <Text key={`${event.action}-${event.outcome}-${index}`}>
            {event.action} · {event.outcome} · {event.total}
          </Text>)}
        </Stack></Card>}
      </Stack>
    </Container>
  );
}
