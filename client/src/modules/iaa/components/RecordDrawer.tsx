import { useState } from "react";
import {
  Anchor, Badge, Button, Divider, Drawer, Group, SegmentedControl, Stack, Text, Textarea,
  TextInput, Timeline,
} from "@mantine/core";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAddDocument, useAnswerQuery, useDecide, useHistory, useProcess, useRaiseQuery, useRecord,
  useSubmit, useValidate,
} from "../api/hooks";
import type { RecordDetail } from "../api/types";
import { done, failed } from "./toast";

const CAN_DOCUMENT = new Set(["draft", "query_raised"]);
const FINANCE_REVIEW = new Set(["submitted", "query_responded"]);
const AWAITING_AUTHORITY = new Set(["finance_validated", "approval_pending", "escalated"]);
const TO_RECORD = new Set(["approved", "verified"]);

function OwnerActions({ r }: { r: RecordDetail }) {
  const [title, setTitle] = useState("");
  const [link, setLink] = useState("");
  const [answer, setAnswer] = useState("");
  const addDoc = useAddDocument();
  const submit = useSubmit();
  const respond = useAnswerQuery();
  const openQuery = r.queries.find((q) => !q.responded_at);
  return (
    <Stack gap="sm">
      {CAN_DOCUMENT.has(r.status) && (
        <Group align="end" wrap="nowrap">
          <TextInput label="Document title" value={title}
            onChange={(e) => setTitle(e.currentTarget.value)} />
          <TextInput label="https:// link" value={link} style={{ flex: 1 }}
            onChange={(e) => setLink(e.currentTarget.value)} />
          <Button variant="light" disabled={!title || !link} loading={addDoc.isPending}
            onClick={() => addDoc.mutateAsync({ id: r.id, title, link })
              .then(() => { setTitle(""); setLink(""); done("Document attached."); })
              .catch(failed)}>Attach</Button>
        </Group>
      )}
      {r.status === "draft" && (
        <Button loading={submit.isPending}
          onClick={() => submit.mutateAsync(r.id).then(() => done("Submitted to Finance."))
            .catch(failed)}>Submit to Finance</Button>
      )}
      {r.status === "query_raised" && openQuery && (
        <Stack gap={6}>
          <Text size="sm" fw={600}>Finance asks: {openQuery.question}</Text>
          <Textarea label="Your answer" value={answer} autosize minRows={2}
            onChange={(e) => setAnswer(e.currentTarget.value)} />
          <Button disabled={!answer.trim()} loading={respond.isPending}
            onClick={() => respond.mutateAsync({ id: r.id, text: answer })
              .then(() => { setAnswer(""); done("Answer sent to Finance."); }).catch(failed)}>
            Send answer
          </Button>
        </Stack>
      )}
    </Stack>
  );
}

function FinanceActions({ r, canReview, canRecord }: {
  r: RecordDetail; canReview: boolean; canRecord: boolean;
}) {
  const [question, setQuestion] = useState("");
  const [remarks, setRemarks] = useState("");
  const [reference, setReference] = useState("");
  const raise = useRaiseQuery();
  const validate = useValidate();
  const process = useProcess();
  if (canReview && FINANCE_REVIEW.has(r.status)) {
    return (
      <Stack gap="sm">
        <Textarea label="Ask the creator (clarification)" value={question} autosize minRows={2}
          onChange={(e) => setQuestion(e.currentTarget.value)} />
        <Button variant="light" disabled={!question.trim()} loading={raise.isPending}
          onClick={() => raise.mutateAsync({ id: r.id, text: question })
            .then(() => { setQuestion(""); done("Query sent."); }).catch(failed)}>
          Raise query
        </Button>
        <Textarea label="Remarks" value={remarks} autosize minRows={2}
          onChange={(e) => setRemarks(e.currentTarget.value)} />
        <Group>
          <Button loading={validate.isPending}
            onClick={() => validate.mutateAsync({ id: r.id, decision: "verify", remarks })
              .then(() => done(r.kind === "ta" ? "Claim verified." : "Request validated."))
              .catch(failed)}>
            {r.kind === "ta" ? "Verify claim" : "Validate request"}
          </Button>
          {r.kind === "ta" && (
            <Button color="red" variant="light" disabled={!remarks.trim()}
              onClick={() => validate.mutateAsync({ id: r.id, decision: "reject", remarks })
                .then(() => done("Claim rejected.")).catch(failed)}>
              Reject (policy)
            </Button>
          )}
        </Group>
      </Stack>
    );
  }
  if (canRecord && TO_RECORD.has(r.status)) {
    return (
      <Stack gap="sm">
        <Text size="sm" c="dimmed">Records internal completion only. No payment is made.</Text>
        <TextInput label="Processing reference" value={reference}
          onChange={(e) => setReference(e.currentTarget.value)} />
        <Button disabled={!reference.trim()} loading={process.isPending}
          onClick={() => process.mutateAsync({ id: r.id, reference, note: "" })
            .then(() => done("Recorded.")).catch(failed)}>Record processing</Button>
      </Stack>
    );
  }
  return null;
}

function ApproverActions({ r }: { r: RecordDetail }) {
  const [decision, setDecision] = useState("approve");
  const [remarks, setRemarks] = useState("");
  const decide = useDecide();
  if (!AWAITING_AUTHORITY.has(r.status)) return null;
  return (
    <Stack gap="sm">
      <SegmentedControl value={decision} onChange={setDecision}
        data={[{ value: "approve", label: "Approve" }, { value: "reject", label: "Reject" }]} />
      <Textarea label="Remarks (required)" value={remarks} autosize minRows={2}
        onChange={(e) => setRemarks(e.currentTarget.value)} />
      <Button color={decision === "reject" ? "red" : undefined} disabled={!remarks.trim()}
        loading={decide.isPending}
        onClick={() => decide.mutateAsync({ id: r.id, decision, remarks })
          .then(() => { setRemarks(""); done("Decision recorded."); }).catch(failed)}>
        Record decision
      </Button>
    </Stack>
  );
}

export function RecordDrawer({ id, onClose }: { id: number | null; onClose: () => void }) {
  const { data: r, error } = useRecord(id);
  const { data: history } = useHistory(id);
  const { can, session } = useAuth();
  const mine = Boolean(r && session && r.user_id === session.user.id);
  return (
    <Drawer opened={id !== null} onClose={onClose} position="right" size="lg"
      title={r ? `${r.kind === "ta" ? "TA claim" : "Request"} #${r.id}` : "Loading…"}>
      {error && <ErrorState error={error} />}
      {r && (
        <Stack gap="md">
          <Group><StatusBadge status={r.status} />
            {r.financial_year && <Badge variant="outline">{r.financial_year}</Badge>}</Group>
          <Text fw={600}>{r.title || r.purpose || "Untitled draft"}</Text>
          {r.description && <Text size="sm">{r.description}</Text>}
          <Text size="sm">Department: {r.department || "—"} · Amount: {r.amount ?? "—"}</Text>
          {r.kind === "ta" && <Text size="sm">Trip: {r.trip_start} → {r.trip_end}</Text>}
          {r.route_levels.length > 0 && (
            <Text size="sm">Approval route: {r.route_levels.join(" → ")}</Text>
          )}
          <Divider label="Documents" />
          {r.documents.length === 0 && <Text size="sm" c="dimmed">None attached.</Text>}
          {r.documents.map((d) => (
            <Anchor key={d.id} href={d.link} target="_blank" rel="noreferrer" size="sm">
              {d.title}
            </Anchor>
          ))}
          <Divider label="Action" />
          {mine && can("iaa.request.create") && <OwnerActions r={r} />}
          {(can("iaa.request.review") || can("iaa.processing.create")) && (
            <FinanceActions r={r} canReview={can("iaa.request.review")}
              canRecord={can("iaa.processing.create")} />
          )}
          {can("iaa.request.approve") && <ApproverActions r={r} />}
          <Divider label="History" />
          <Timeline bulletSize={12} lineWidth={2}>
            {(history ?? []).map((h) => (
              <Timeline.Item key={h.id} title={h.action.replace(/_/g, " ")}>
                <Text size="xs" c="dimmed">
                  {new Date(h.created_at).toLocaleString()} · {h.actor_role}
                  {h.to_status && ` · ${h.to_status.replace(/_/g, " ")}`}
                </Text>
                {h.remarks && <Text size="sm">{h.remarks}</Text>}
              </Timeline.Item>
            ))}
          </Timeline>
        </Stack>
      )}
    </Drawer>
  );
}
