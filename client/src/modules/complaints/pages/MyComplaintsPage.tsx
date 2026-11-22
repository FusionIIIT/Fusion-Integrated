import { useState } from "react";
import { Alert, Anchor, Badge, Button, Card, Container, FileInput, Group, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useComplaintAttachments, useMyComplaints, useRequestReopening, useSubmitComplaint, useSubmitFeedback, useUploadComplaintAttachment, useVerifyClosure } from "../api/hooks";
import type { Complaint } from "../api/types";

const CREATE = "complaints.complaint.create";
const FEEDBACK = "complaints.feedback.create";

export default function MyComplaintsPage() {
  const { can } = useAuth();
  const query = useMyComplaints();
  const submit = useSubmitComplaint();
  const feedback = useSubmitFeedback();
  const reopen = useRequestReopening();
  const verify = useVerifyClosure();
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");
  const [submissionFiles, setSubmissionFiles] = useState<File[]>([]);
  const [messages, setMessages] = useState<Record<string, string>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});

  function create() {
    submit.mutate({ category, description, attachments: submissionFiles }, {
      onSuccess: () => { setCategory(""); setDescription(""); setSubmissionFiles([]); notifications.show({ color: "green", title: "Complaint submitted", message: "Your complaint was recorded." }); },
      onError: (e) => notifications.show({ color: "red", title: "Could not submit", message: errorMessage(e) }),
    });
  }

  if (query.error) return <Container size="lg"><ErrorState error={query.error} /></Container>;
  return (
    <Container size="lg">
      <PageHeader title="My Complaints" subtitle="Submit a complaint and follow its status and history." />
      {can(CREATE) && <Card withBorder padding="lg" mb="lg">
        <Stack>
          <Text fw={600}>Submit a complaint</Text>
          <TextInput label="Category" value={category} onChange={(e) => setCategory(e.currentTarget.value)} required />
          <Textarea label="Description" minRows={4} autosize value={description} onChange={(e) => setDescription(e.currentTarget.value)} required />
          <FileInput label="Supporting evidence (optional; up to 5 PDF, JPEG, or PNG files, 5 MB each)" multiple value={submissionFiles} onChange={setSubmissionFiles} accept="application/pdf,image/jpeg,image/png" />
          <Group justify="flex-end"><Button onClick={create} loading={submit.isPending} disabled={!category.trim() || !description.trim()}>Submit complaint</Button></Group>
        </Stack>
      </Card>}
      <Stack>
        {(query.data?.results ?? []).map((complaint) => <ComplaintCard key={complaint.reference} complaint={complaint}
          canFeedback={can(FEEDBACK)} message={messages[complaint.reference] ?? ""}
          reason={reasons[complaint.reference] ?? ""}
          setMessage={(v) => setMessages((old) => ({ ...old, [complaint.reference]: v }))}
          setReason={(v) => setReasons((old) => ({ ...old, [complaint.reference]: v }))}
          onFeedback={() => feedback.mutate({ reference: complaint.reference, message: messages[complaint.reference] ?? "" }, { onSuccess: () => notifications.show({ color: "green", title: "Feedback submitted", message: "Thank you for your feedback." }), onError: (e) => notifications.show({ color: "red", title: "Could not submit feedback", message: errorMessage(e) }) })}
          onReopen={() => reopen.mutate({ reference: complaint.reference, reason: reasons[complaint.reference] ?? "" }, { onSuccess: () => notifications.show({ color: "green", title: "Request submitted", message: "Your reopening request was sent for review." }), onError: (e) => notifications.show({ color: "red", title: "Could not request reopening", message: errorMessage(e) }) })}
          onVerify={() => verify.mutate(complaint.reference, { onSuccess: () => notifications.show({ color: "green", title: "Complaint closed", message: "Your verification was recorded." }), onError: (e) => notifications.show({ color: "red", title: "Could not verify", message: errorMessage(e) }) })}
          busy={feedback.isPending || reopen.isPending || verify.isPending} />)}
        {query.isLoading && <Text c="dimmed">Loading your complaints…</Text>}
        {!query.isLoading && (query.data?.results.length ?? 0) === 0 && <Alert color="gray">You have not submitted any complaints yet.</Alert>}
      </Stack>
    </Container>
  );
}

function ComplaintCard({ complaint, canFeedback, message, reason, setMessage, setReason, onFeedback, onReopen, onVerify, busy }: {
  complaint: Complaint; canFeedback: boolean; message: string; reason: string;
  setMessage: (value: string) => void; setReason: (value: string) => void;
  onFeedback: () => void; onReopen: () => void; onVerify: () => void; busy: boolean;
}) {
  const attachments = useComplaintAttachments(complaint.reference);
  const upload = useUploadComplaintAttachment(complaint.reference);
  return <Card withBorder padding="lg">
    <Stack>
      <Group justify="space-between" align="flex-start">
        <div><Text fw={600}>{complaint.category}</Text><Text size="xs" c="dimmed">Ref {complaint.reference} · {new Date(complaint.submitted_at).toLocaleString()}</Text></div>
        <Badge variant="light">{complaint.status.replaceAll("_", " ")}</Badge>
      </Group>
      <Text style={{ whiteSpace: "pre-wrap" }}>{complaint.description}</Text>
      {complaint.resolution_details && <Alert color="green" title="Resolution">{complaint.resolution_details}</Alert>}
      {complaint.rejection_reason && <Alert color="red" title="Outcome">{complaint.rejection_reason}</Alert>}
      <Stack gap="xs"><Text fw={500} size="sm">Attachments</Text>
        {attachments.data?.results.map((file) => <Anchor key={file.id} href={`/api/v1/complaints/attachments/${file.id}/download`} target="_blank" rel="noreferrer">{file.original_name} · {Math.ceil(file.byte_size / 1024)} KB</Anchor>)}
        {complaint.status === "submitted" || complaint.status === "in_progress" ? <FileInput label="Add PDF, JPEG, or PNG (max 5 MB)" accept="application/pdf,image/jpeg,image/png" clearable onChange={(file) => file && upload.mutate(file, { onSuccess: () => notifications.show({ color: "green", title: "Attachment uploaded", message: "The file was added to this complaint." }), onError: (e) => notifications.show({ color: "red", title: "Could not upload attachment", message: errorMessage(e) }) })} /> : null}
      </Stack>
      {!!complaint.history.length && <Stack gap={4}><Text size="sm" fw={500}>History</Text>{complaint.history.map((event, index) => <Text key={`${event.event}-${index}`} size="sm" c="dimmed">{new Date(event.occurred_at).toLocaleString()} · {event.event.replaceAll("_", " ")}{event.details ? ` — ${event.details}` : ""}</Text>)}</Stack>}
      {complaint.status === "resolved" && complaint.verification_required && <Button variant="light" onClick={onVerify} loading={busy}>Verify resolution and close</Button>}
      {canFeedback && (complaint.status === "resolved" || complaint.status === "closed") && !complaint.feedback_submitted && <Group align="flex-end"><Textarea label="Feedback" value={message} onChange={(e) => setMessage(e.currentTarget.value)} /><Button onClick={onFeedback} loading={busy} disabled={!message.trim()}>Send feedback</Button></Group>}
      {complaint.feedback_submitted && <Text size="sm" c="dimmed">Feedback submitted.</Text>}
      {complaint.status === "closed" && complaint.reopening_status === "pending" && <Text size="sm" c="dimmed">Your reopening request is awaiting supervisor review.</Text>}
      {complaint.reopening_status === "approved" && complaint.status === "in_progress" && <Alert color="blue">Your reopening request was approved. The complaint has returned to active handling.</Alert>}
      {complaint.status === "closed" && complaint.reopening_status !== "pending" && complaint.reopening_status !== "approved" && <Group align="flex-end"><Textarea label="Why are you dissatisfied?" value={reason} onChange={(e) => setReason(e.currentTarget.value)} /><Button variant="default" onClick={onReopen} loading={busy} disabled={!reason.trim()}>Request reopening</Button></Group>}
    </Stack>
  </Card>;
}
