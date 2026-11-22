import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, Modal, Stack, Table, Text,
  Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAppraisals, useAssignReviewers, useReviewAppraisal, useSubmitAppraisal,
} from "../api/hooks";
import type { Appraisal } from "../api/types";

export default function AppraisalsPage() {
  const { can } = useAuth();
  const { data, isPending, error } = useAppraisals();
  const [creating, setCreating] = useState(false);
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;
  return (
    <Container size="xl">
      <PageHeader title="Yearly Appraisals" subtitle="Submit and review appraisal records"
        action={can("hr.appraisal.create") && <Button onClick={() => setCreating(true)}>Submit appraisal</Button>} />
      <Card withBorder>
        {isPending ? <Text>Loading appraisals…</Text> : data?.results.length ? (
          <Table.ScrollContainer minWidth={900}><Table striped>
            <Table.Thead><Table.Tr><Table.Th>Appraisal</Table.Th><Table.Th>Employee</Table.Th>
              <Table.Th>Period</Table.Th><Table.Th>Status</Table.Th><Table.Th>Current reviewer</Table.Th>
              <Table.Th>Actions</Table.Th></Table.Tr></Table.Thead>
            <Table.Tbody>{data.results.map((appraisal) => (
              <Table.Tr key={appraisal.id}><Table.Td>#{appraisal.id}</Table.Td>
                <Table.Td>{appraisal.employee_user_id}</Table.Td><Table.Td>{appraisal.period}</Table.Td>
                <Table.Td><Badge>{appraisal.status_display}</Badge></Table.Td>
                <Table.Td>{appraisal.current_reviewer_user_id ?? "—"}</Table.Td>
                <Table.Td><AppraisalActions appraisal={appraisal} /></Table.Td></Table.Tr>
            ))}</Table.Tbody>
          </Table></Table.ScrollContainer>
        ) : <Text c="dimmed">No appraisals are available.</Text>}
      </Card>
      {creating && <AppraisalEditor onClose={() => setCreating(false)} />}
    </Container>
  );
}

function AppraisalActions({ appraisal }: { appraisal: Appraisal }) {
  const { can, session } = useAuth();
  const [assigning, setAssigning] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const isCurrentReviewer = appraisal.current_reviewer_user_id === session?.user.id;
  return <Group gap="xs">
    {can("hr.appraisal.assign") && appraisal.status === "submitted" &&
      <Button size="xs" onClick={() => setAssigning(true)}>Assign reviewers</Button>}
    {can("hr.appraisal.review") && isCurrentReviewer &&
      appraisal.employee_user_id !== session?.user.id &&
      ["pending_review", "pending_next_authority"].includes(appraisal.status) &&
      <Button size="xs" onClick={() => setReviewing(true)}>Review</Button>}
    {assigning && <ReviewerEditor appraisalId={appraisal.id} onClose={() => setAssigning(false)} />}
    {reviewing && <ReviewEditor appraisal={appraisal} onClose={() => setReviewing(false)} />}
  </Group>;
}

function AppraisalEditor({ onClose }: { onClose: () => void }) {
  const submit = useSubmitAppraisal();
  const [period, setPeriod] = useState("");
  const [formData, setFormData] = useState("{}");
  function save() {
    try {
      const value = JSON.parse(formData) as Record<string, unknown>;
      if (!value || Array.isArray(value) || typeof value !== "object") throw new Error("Enter a JSON object.");
      submit.mutate({ period, form_data: value }, {
        onSuccess: () => { notifications.show({ color: "green", title: "Appraisal submitted", message: "Your appraisal was submitted." }); onClose(); },
        onError: (e) => notifications.show({ color: "red", title: "Could not submit appraisal", message: errorMessage(e) }),
      });
    } catch (e) {
      notifications.show({ color: "red", title: "Invalid appraisal form", message: e instanceof Error ? e.message : errorMessage(e) });
    }
  }
  return <Modal opened onClose={onClose} title="Submit yearly appraisal" size="lg"><Stack>
    <TextInput label="Appraisal period" placeholder="For example, 2026" required
      value={period} onChange={(e) => setPeriod(e.currentTarget.value)} />
    <Textarea label="Appraisal form information (JSON)" minRows={7} value={formData}
      onChange={(e) => setFormData(e.currentTarget.value)} />
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancel</Button>
      <Button loading={submit.isPending} disabled={!period.trim()} onClick={save}>Submit appraisal</Button></Group>
  </Stack></Modal>;
}

function ReviewerEditor({ appraisalId, onClose }: { appraisalId: number; onClose: () => void }) {
  const assign = useAssignReviewers(appraisalId);
  const [reviewers, setReviewers] = useState("");
  function save() {
    const ids = reviewers.split(",").map((value) => Number(value.trim()));
    if (!ids.length || ids.some((id) => !Number.isSafeInteger(id) || id < 1)) {
      notifications.show({ color: "red", title: "Invalid reviewers", message: "Enter employee IDs separated by commas." });
      return;
    }
    assign.mutate({ reviewer_user_ids: ids }, {
      onSuccess: () => { notifications.show({ color: "green", title: "Reviewers assigned", message: "The first reviewer was notified." }); onClose(); },
      onError: (e) => notifications.show({ color: "red", title: "Could not assign reviewers", message: errorMessage(e) }),
    });
  }
  return <Modal opened onClose={onClose} title="Assign appraisal reviewers"><Stack>
    <TextInput label="Reviewer employee IDs, in order" placeholder="123, 456"
      value={reviewers} onChange={(e) => setReviewers(e.currentTarget.value)} />
    <Text size="xs" c="dimmed">Reviewers act in order; the next reviewer is notified after forwarding.</Text>
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancel</Button>
      <Button loading={assign.isPending} onClick={save}>Assign</Button></Group>
  </Stack></Modal>;
}

function ReviewEditor({ appraisal, onClose }: { appraisal: Appraisal; onClose: () => void }) {
  const review = useReviewAppraisal(appraisal.id);
  const [note, setNote] = useState("");
  function submit(action: "forward" | "finalize") {
    review.mutate({ action, note }, {
      onSuccess: () => {
        notifications.show({ color: "green", title: action === "forward" ? "Appraisal forwarded" : "Appraisal finalized",
          message: action === "forward" ? "The next reviewer was notified." : "The employee was notified." });
        onClose();
      },
      onError: (e) => notifications.show({ color: "red", title: "Could not update appraisal", message: errorMessage(e) }),
    });
  }
  return <Modal opened onClose={onClose} title={`Review appraisal ${appraisal.period}`} size="lg"><Stack>
    <Text size="sm">Employee {appraisal.employee_user_id}</Text>
    <Textarea label="Submitted appraisal form (JSON)" minRows={6}
      value={JSON.stringify(appraisal.form_data, null, 2)} readOnly />
    <Textarea label="Review note" value={note} minRows={3}
      onChange={(e) => setNote(e.currentTarget.value)} />
    <Group justify="flex-end"><Button variant="default" onClick={onClose}>Cancel</Button>
      <Button loading={review.isPending} onClick={() => submit("forward")}>Forward</Button>
      <Button color="green" loading={review.isPending} onClick={() => submit("finalize")}>Finalize</Button></Group>
  </Stack></Modal>;
}