import { useState } from "react";
import {
  Badge, Button, Card, Container, Drawer, Group, NumberInput, Select, Stack, Switch,
  Text, Textarea, Timeline,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaClipboardList, FaHistory } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { Field, FormRow, FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCorrectRecord, useOfficeRecords, useRecordRevisions, useSeasons,
} from "../api/hooks";
import type { OfficeRecord } from "../api/types";
import { LoadMore } from "../components/LoadMore";

const KINDS = [
  { value: "fte", label: "Full time" },
  { value: "internship", label: "Internship" },
  { value: "ppo", label: "Pre-placement offer" },
];

function kindLabel(kind: string) {
  return KINDS.find((k) => k.value === kind)?.label ?? kind;
}

function CorrectModal({ record, onClose }: {
  record: OfficeRecord | null; onClose: () => void;
}) {
  const correct = useCorrectRecord();
  const [reason, setReason] = useState("");
  const [ctc, setCtc] = useState<number | string>(record?.ctc_lpa ?? "");
  const [kind, setKind] = useState<string | null>(record?.kind ?? null);
  const [active, setActive] = useState(record?.is_active ?? true);

  if (!record) return null;

  function submit() {
    if (!record) return;
    correct.mutate({
      id: record.id, reason,
      ctc_lpa: ctc === "" ? null : String(ctc),
      kind: (kind ?? record.kind) as OfficeRecord["kind"],
      is_active: active,
    }, {
      onSuccess: () => {
        notifications.show({ color: "green", title: "Record corrected",
          message: "The previous values are kept in the record's history." });
        onClose();
      },
    });
  }

  return (
    <FormModal
      opened onClose={onClose} title="Correct placement record"
      subtitle={`${record.company?.name ?? "—"} · ${record.season}`}
      onSubmit={submit} submitLabel="Save correction" submitting={correct.isPending}
      error={correct.error} disabled={!reason.trim()}
      disabledReason="Give the reason for this correction."
    >
      <Stack gap="lg">
        <FormSection first title="Placement">
          <FormRow>
            <Field span={6}>
              <NumberInput label="Package (LPA)" min={0} decimalScale={2} value={ctc}
                onChange={setCtc} />
            </Field>
            <Field span={6}>
              <Select label="Type" data={KINDS} value={kind} onChange={setKind}
                allowDeselect={false} />
            </Field>
            <Field span={12}>
              <Switch label="Active placement" checked={active}
                onChange={(e) => setActive(e.currentTarget.checked)} />
            </Field>
          </FormRow>
        </FormSection>
        <FormSection title="Why" hint="Kept with the record's history.">
          <Textarea label="Reason" required autosize minRows={2} maxLength={300}
            value={reason} onChange={(e) => setReason(e.currentTarget.value)} />
        </FormSection>
      </Stack>
    </FormModal>
  );
}

function HistoryPanel({ record, onClose }: {
  record: OfficeRecord | null; onClose: () => void;
}) {
  const { data, isPending, error } = useRecordRevisions(record?.id);
  return (
    <Drawer opened={record !== null} onClose={onClose} position="right"
      size="md" title={<Text fw={700}>Correction history</Text>}>
      {error && <ErrorState error={error} />}
      {isPending && !error && <Text size="sm" c="dimmed">Loading…</Text>}
      {data && data.length === 0 && (
        <Text size="sm" c="dimmed">This record has never been corrected.</Text>
      )}
      {data && data.length > 0 && (
        <Timeline active={data.length} bulletSize={16} lineWidth={2}>
          {data.map((r) => (
            <Timeline.Item key={r.id}
              title={<Text size="sm" fw={600}>{new Date(r.created_at).toLocaleString()}</Text>}>
              <Text size="sm">{r.reason}</Text>
              <Text size="xs" c="dimmed">
                {r.before.ctc_lpa ?? "—"} → {r.after.ctc_lpa ?? "—"} LPA ·{" "}
                {kindLabel(r.before.kind)} → {kindLabel(r.after.kind)} ·{" "}
                {r.before.is_active ? "active" : "inactive"} →{" "}
                {r.after.is_active ? "active" : "inactive"}
              </Text>
            </Timeline.Item>
          ))}
        </Timeline>
      )}
    </Drawer>
  );
}

export default function RecordsPage() {
  const [season, setSeason] = useState<string | undefined>(undefined);
  const seasons = useSeasons();
  const list = useOfficeRecords(season);
  const { data, isPending, error } = list;
  const [editing, setEditing] = useState<OfficeRecord | null>(null);
  const [history, setHistory] = useState<OfficeRecord | null>(null);

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Placement Records"
        subtitle="Correct a student's or alumnus's recorded placement"
        action={
          <Select
            label="Season" size="xs" w={140} clearable placeholder="All seasons"
            data={(seasons.data ?? []).map((s) => s.season)}
            value={season ?? null} onChange={(v) => setSeason(v ?? undefined)}
          />
        }
      />
      <Card padding="lg">
        <DataTable<OfficeRecord>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "user_id", header: "Person", render: (r) => `#${r.user_id}` },
            { key: "company", header: "Company", render: (r) => r.company?.name ?? "—" },
            { key: "season", header: "Season", render: (r) => r.season },
            { key: "kind", header: "Type", render: (r) => kindLabel(r.kind) },
            { key: "ctc_lpa", header: "Package (LPA)", align: "right",
              render: (r) => r.ctc_lpa ?? "—" },
            { key: "is_active", header: "Status",
              render: (r) => (
                <Badge color={r.is_active ? "green" : "gray"} variant="light">
                  {r.is_active ? "Active" : "Inactive"}
                </Badge>
              ) },
            { key: "actions", header: "", align: "right",
              render: (r) => (
                <Group gap="xs" justify="flex-end">
                  <Button size="xs" variant="subtle" leftSection={<FaHistory size={11} />}
                    onClick={() => setHistory(r)}>
                    History
                  </Button>
                  <Button size="xs" variant="light" onClick={() => setEditing(r)}>
                    Correct
                  </Button>
                </Group>
              ) },
          ]}
          empty={{
            icon: FaClipboardList,
            title: "No placement records",
            description: "A record appears when a student accepts an offer or the "
              + "office records an off-campus placement.",
          }}
        />
      </Card>
      <CorrectModal key={editing?.id ?? 0} record={editing} onClose={() => setEditing(null)} />
      <HistoryPanel record={history} onClose={() => setHistory(null)} />
      <LoadMore list={list} />
    </Container>
  );
}
