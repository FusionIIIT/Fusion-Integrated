import { useState } from "react";
import {
  Button, Card, Container, Group, NumberInput, SegmentedControl, Stack, Text, TextInput, Textarea,
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useObservations, useRaiseObservation, useRespondObservation, useReviewObservation,
} from "../api/hooks";
import type { Observation } from "../api/types";
import { done, failed } from "../components/toast";

function ObservationCard({ o }: { o: Observation }) {
  const { can, session } = useAuth();
  const [action, setAction] = useState("");
  const [link, setLink] = useState("");
  const [verdict, setVerdict] = useState("satisfactory");
  const respond = useRespondObservation();
  const review = useReviewObservation();
  const isRespondent = session?.user.id === o.respondent_user_id;
  return (
    <Card padding="md">
      <Group justify="space-between">
        <Text fw={600}>#{o.id} · {o.title}{o.record ? ` · item #${o.record}` : ""}</Text>
        <StatusBadge status={o.status} />
      </Group>
      <Text size="sm" mt={4}>{o.detail}</Text>
      {o.responses.map((r) => (
        <Text key={r.id} size="xs" c="dimmed" mt={4}>
          Cycle {r.cycle}: {r.corrective_action} — {r.verdict}
          {r.review_remarks && ` (${r.review_remarks})`}
        </Text>
      ))}
      {o.status === "open" && isRespondent && can("iaa.observation.update") && (
        <Stack gap={6} mt="sm">
          <Textarea label="Corrective action taken" value={action} autosize minRows={2}
            onChange={(e) => setAction(e.currentTarget.value)} />
          <TextInput label="Evidence link (https://)" value={link}
            onChange={(e) => setLink(e.currentTarget.value)} />
          <Button size="xs" disabled={!action.trim()} loading={respond.isPending}
            onClick={() => respond.mutateAsync({ id: o.id, corrective_action: action,
                                                 evidence_link: link })
              .then(() => done("Response sent to the Auditor.")).catch(failed)}>
            Send response</Button>
        </Stack>
      )}
      {o.status === "responded" && can("iaa.observation.review") && (
        <Stack gap={6} mt="sm">
          <SegmentedControl value={verdict} onChange={setVerdict}
            data={[{ value: "satisfactory", label: "Close" },
                   { value: "unsatisfactory", label: "Return for another response" }]} />
          <Textarea label="Remarks" value={action} autosize minRows={2}
            onChange={(e) => setAction(e.currentTarget.value)} />
          <Button size="xs" loading={review.isPending}
            disabled={verdict === "unsatisfactory" && !action.trim()}
            onClick={() => review.mutateAsync({ id: o.id, verdict, remarks: action })
              .then(() => done("Review recorded.")).catch(failed)}>Record review</Button>
        </Stack>
      )}
    </Card>
  );
}

export default function ObservationsPage() {
  const { data, isPending, error } = useObservations();
  const { can } = useAuth();
  const raise = useRaiseObservation();
  const [raising, setRaising] = useState(false);
  const [title, setTitle] = useState("");
  const [detail, setDetail] = useState("");
  const [recordId, setRecordId] = useState<number | string>("");
  const [respondent, setRespondent] = useState<number | string>("");
  if (error) return <Container size="md"><ErrorState error={error} /></Container>;
  const rows = data?.results ?? [];
  return (
    <Container size="md">
      <PageHeader title="Audit observations" subtitle="Open → Responded → Closed"
        action={can("iaa.observation.create") && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setRaising(true)}>
            Raise observation</Button>)} />
      {isPending && <Text c="dimmed">Loading…</Text>}
      {!isPending && rows.length === 0 && (
        <Card padding="xl"><Text fw={600} ta="center">No audit observations</Text></Card>
      )}
      <Stack gap="sm">{rows.map((o) => <ObservationCard key={o.id} o={o} />)}</Stack>
      <FormModal opened={raising} onClose={() => setRaising(false)}
        title="Raise an audit observation" submitLabel="Raise" submitting={raise.isPending}
        error={raise.error} disabled={!title.trim() || !detail.trim()}
        disabledReason="Give a title and the finding."
        onSubmit={() => raise.mutateAsync({
          title, detail, record_id: recordId === "" ? null : Number(recordId),
          respondent_user_id: respondent === "" ? null : Number(respondent),
        }).then(() => { setRaising(false); setTitle(""); setDetail("");
                        done("Observation raised."); }).catch(() => undefined)}>
        <Stack gap="sm" p="lg">
          <TextInput label="Title" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
          <Textarea label="Finding" value={detail} autosize minRows={3}
            onChange={(e) => setDetail(e.currentTarget.value)} />
          <NumberInput label="Request / claim number (optional)" value={recordId}
            onChange={setRecordId} min={1} />
          <NumberInput label="Respondent user id (if no item is linked)" value={respondent}
            onChange={setRespondent} min={1} />
        </Stack>
      </FormModal>
    </Container>
  );
}
