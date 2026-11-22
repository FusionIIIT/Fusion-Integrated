import { useState } from "react";
import {
  Button, Card, Container, Group, NumberInput, Select, Stack, Text, Textarea,
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAnomalies, useAnomalyAction, useFlagAnomaly } from "../api/hooks";
import type { Anomaly } from "../api/types";
import { done, failed } from "../components/toast";

function AnomalyCard({ a, mayReview, role }: { a: Anomaly; mayReview: boolean; role: string }) {
  const [text, setText] = useState("");
  const act = useAnomalyAction();
  const mine = mayReview && a.status !== "resolved" && a.assigned_role === role;
  return (
    <Card padding="md">
      <Group justify="space-between">
        <Text fw={600}>#{a.id} · {a.category} ({a.source})
          {a.record ? ` · item #${a.record}` : ""}</Text>
        <StatusBadge status={a.status} />
      </Group>
      <Text size="sm" mt={4}>{a.description}</Text>
      <Text size="xs" c="dimmed" mt={4}>With: {a.assigned_role}
        {a.resolution && ` · Resolution: ${a.resolution}`}</Text>
      {mine && (
        <Stack gap={6} mt="sm">
          <Textarea label="Resolution or escalation reason" value={text} autosize minRows={2}
            onChange={(e) => setText(e.currentTarget.value)} />
          <Group>
            <Button size="xs" disabled={!text.trim()} loading={act.isPending}
              onClick={() => act.mutateAsync({ id: a.id, action: "resolve", text })
                .then(() => done("Anomaly resolved.")).catch(failed)}>Resolve</Button>
            {a.resolver_level + 1 < a.resolver_chain.length && (
              <Button size="xs" variant="light" disabled={!text.trim()}
                onClick={() => act.mutateAsync({ id: a.id, action: "escalate", text })
                  .then(() => done("Anomaly escalated.")).catch(failed)}>Escalate</Button>
            )}
          </Group>
        </Stack>
      )}
    </Card>
  );
}

export default function AnomaliesPage() {
  const { data, isPending, error } = useAnomalies();
  const { can, session } = useAuth();
  const [flagging, setFlagging] = useState(false);
  const [category, setCategory] = useState<string | null>("policy");
  const [description, setDescription] = useState("");
  const [recordId, setRecordId] = useState<number | string>("");
  const flag = useFlagAnomaly();
  if (error) return <Container size="md"><ErrorState error={error} /></Container>;
  const rows = data?.results ?? [];
  return (
    <Container size="md">
      <PageHeader title="Anomalies" subtitle="Material policy, budget and financial anomalies"
        action={can("iaa.anomaly.create") && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setFlagging(true)}>
            Flag anomaly</Button>)} />
      {isPending && <Text c="dimmed">Loading…</Text>}
      {!isPending && rows.length === 0 && (
        <Card padding="xl"><Text fw={600} ta="center">No anomalies in your scope</Text></Card>
      )}
      <Stack gap="sm">
        {rows.map((a) => (
          <AnomalyCard key={a.id} a={a} mayReview={can("iaa.anomaly.review")}
            role={session?.active_role ?? ""} />
        ))}
      </Stack>
      <FormModal opened={flagging} onClose={() => setFlagging(false)} title="Flag an anomaly"
        submitLabel="Flag" submitting={flag.isPending} error={flag.error}
        disabled={!category || !description.trim()}
        disabledReason="Choose a category and describe the anomaly."
        onSubmit={() => flag.mutateAsync({ category: category ?? "policy", description,
                                           record_id: recordId === "" ? null : Number(recordId) })
          .then(() => { setFlagging(false); setDescription(""); done("Anomaly flagged."); })
          .catch(() => undefined)}>
        <Stack gap="sm" p="lg">
          <Select label="Category" value={category} onChange={setCategory}
            data={["budget", "policy", "financial"]} />
          <NumberInput label="Request / claim number (optional)" value={recordId}
            onChange={setRecordId} min={1} />
          <Textarea label="What is anomalous?" value={description} autosize minRows={3}
            onChange={(e) => setDescription(e.currentTarget.value)} />
        </Stack>
      </FormModal>
    </Container>
  );
}
