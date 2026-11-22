import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Card, Container, FileInput, Group, Select, Stack, Text,
  TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage, http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useArchiveRequests, useDecideArchiveRequest, useSubmitArchiveRequest } from "../api/hooks";
import type { ArchiveRequest } from "../api/types";

export default function ArchivesPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useArchiveRequests();
  const create = useSubmitArchiveRequest();
  const decide = useDecideArchiveRequest();
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [fileDate, setFileDate] = useState("");
  const [owners, setOwners] = useState("");
  const [fileType, setFileType] = useState("");
  const [reason, setReason] = useState("");
  const [classifications, setClassifications] = useState<Record<number, string>>({});
  const queryClient = useQueryClient();
  const rows = data?.results ?? [];

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.set("attachment", file);
    form.set("file_name", fileName);
    form.set("file_date", fileDate);
    form.set("owners", JSON.stringify(owners.split(",").map((v) => v.trim()).filter(Boolean)));
    form.set("file_type", fileType);
    form.set("reason", reason);
    try {
      await create.mutateAsync(form);
      setFile(null);
      notifications.show({ title: "Request submitted", message: "Your HoD can now review it." });
    } catch (submitError) {
      notifications.show({ title: "Could not submit request", message: errorMessage(submitError),
        color: "red" });
    }
  }

  async function decideRequest(row: ArchiveRequest, decision: "approve" | "reject") {
    try {
      await decide.mutateAsync({ id: row.id, decision });
      notifications.show({ title: "Decision recorded", message: `Request ${row.id} updated.` });
    } catch (decisionError) {
      notifications.show({ title: "Could not record decision", message: errorMessage(decisionError),
        color: "red" });
    }
  }

  async function classifyRequest(row: ArchiveRequest) {
    try {
      await http.post(`/badms/archive_requests/${row.id}/classification`, {
        classification: classifications[row.id],
      });
      await queryClient.invalidateQueries({ queryKey: ["badms"] });
    } catch (classifyError) {
      notifications.show({ title: "Could not classify archive", message: errorMessage(classifyError),
        color: "red" });
    }
  }

  async function encryptRequest(row: ArchiveRequest) {
    try {
      await http.post(`/badms/archive_requests/${row.id}/encryption`);
      await queryClient.invalidateQueries({ queryKey: ["badms"] });
    } catch (encryptionError) {
      notifications.show({ title: "Could not create secure archive",
        message: errorMessage(encryptionError), color: "red" });
    }
  }

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  return (
    <Container size="lg">
      <PageHeader title="Secure archives" subtitle="Submit and track archival requests" />
      {can("badms.archive.create") && (
        <Card withBorder padding="lg" mb="lg">
          <form onSubmit={submit}>
            <Stack>
              <Text fw={700}>New request</Text>
              <FileInput label="File" value={file} onChange={setFile} required />
              <TextInput label="File name" value={fileName} onChange={(e) => setFileName(e.currentTarget.value)} required />
              <TextInput label="File date" type="date" value={fileDate} onChange={(e) => setFileDate(e.currentTarget.value)} required />
              <TextInput label="Owners (comma separated)" value={owners} onChange={(e) => setOwners(e.currentTarget.value)} required />
              <TextInput label="File type" value={fileType} onChange={(e) => setFileType(e.currentTarget.value)} required />
              <Textarea label="Reason" value={reason} onChange={(e) => setReason(e.currentTarget.value)} required />
              <Button type="submit" loading={create.isPending}>Submit archive request</Button>
            </Stack>
          </form>
        </Card>
      )}
      {isPending && <Text c="dimmed">Loading requests…</Text>}
      <Stack>
        {rows.map((row) => (
          <Card key={row.id} withBorder padding="lg">
            <Group justify="space-between" align="flex-start">
              <Stack gap={4}>
                <Text fw={700}>{row.file_name}</Text>
                <Text size="sm" c="dimmed">{row.file_type} · {row.department} · {row.file_date}</Text>
                <Text size="sm">{row.reason}</Text>
                <Badge w="fit-content">{row.status}</Badge>
              </Stack>
              {can("badms.archive.review_department") && row.status === "Submitted" && (
                <Group>
                  <Button onClick={() => decideRequest(row, "approve")}>Approve</Button>
                  <Button color="red" variant="light" onClick={() => decideRequest(row, "reject")}>Reject</Button>
                </Group>
              )}
              {can("badms.archive.classify") && row.status === "HoD Approved" && <Stack>
                <Select label="Classification" data={["Critical", "Sensitive", "Routine", "Archival"]}
                  value={classifications[row.id] ?? null}
                  onChange={(value) => setClassifications((old) => ({ ...old, [row.id]: value ?? "" }))} />
                <Button disabled={!classifications[row.id]} onClick={() => classifyRequest(row)}>
                  Apply classification
                </Button>
              </Stack>}
              {can("badms.archive.encrypt") &&
                row.status === "Classified Sensitive / Routed to IT Security" &&
                <Button onClick={() => encryptRequest(row)}>Create encrypted archive</Button>}
            </Group>
          </Card>
        ))}
        {!isPending && rows.length === 0 && (
          <Card withBorder><Text c="dimmed">No archival requests yet.</Text></Card>
        )}
      </Stack>
    </Container>
  );
}
