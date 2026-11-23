import {
  Badge, Button, Center, Drawer, Group, Loader, Select, Stack, Table, Tabs, Text, Title,
} from "@mantine/core";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import * as h from "../api/hooks";
import type { ApplicationDetail, PmsDocument } from "../api/types";
import { ActionBar, action, str } from "./ActionBar";
import { day, money, SENSITIVITY_NAMES, words } from "./format";
import { InventorsModal } from "./InventorsModal";
import { UploadModal } from "./UploadModal";
import { useApplicationActions } from "./useApplicationActions";
import { usePmsCan } from "./access";

const EDITABLE = ["draft", "needs_revision", "rejected"];

function Rows({ rows, empty }: { rows: [string, React.ReactNode][]; empty?: string }) {
  if (!rows.length) return <Text size="sm" c="dimmed">{empty ?? "Nothing recorded yet."}</Text>;
  return (
    <Table withRowBorders={false} verticalSpacing={4}>
      <Table.Tbody>
        {rows.map(([k, v], i) => (
          // A fixed list that is never reordered; labels such as history times can repeat.
          <Table.Tr key={`${i}:${k}`}>
            <Table.Td w={220}><Text size="sm" c="dimmed">{k}</Text></Table.Td>
            <Table.Td><Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{v}</Text></Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

function Overview({ app }: { app: ApplicationDetail }) {
  return (
    <Stack gap="md">
      <Rows rows={[
        ["Reference", app.reference || "Draft"], ["Status", words(app.status)],
        ["Applicant", app.applicant_name], ["Technical area", app.domain_code || "—"],
        ["Submitted", day(app.submitted_at)], ["Resubmit by", day(app.revision_due_on)],
        ["Appeal by", day(app.appeal_due_on)],
        ...(app.patent_number ? [["Patent", `${app.patent_number} (${app.grant_jurisdiction}, `
          + `granted ${day(app.grant_date)})`] as [string, string]] : []),
      ]} />
      {Object.entries(app.feedback).map(([k, v]) => (
        <Stack key={k} gap={2}>
          <Text fw={600} size="sm">{words(k)} feedback</Text>
          <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{v}</Text>
        </Stack>
      ))}
      <Rows rows={[["Abstract", app.abstract || "—"], ["Claims", app.claims || "—"],
        ["Detailed description", app.description || "—"]]} />
    </Stack>
  );
}

function Inventors({ app }: { app: ApplicationDetail }) {
  const { session } = useAuth();
  const can = usePmsCan();
  const [editing, setEditing] = useState(false);
  const agree = h.useRecordAgreement();
  const owner = session?.user.id === app.applicant_user_id;
  const preFiling = !["filed", "granted", "refused", "withdrawn", "expired",
    "rejection_upheld"].includes(app.status);
  const actions = owner && can("pms.inventor.update") && preFiling
    ? app.inventors.filter((i) => !i.agreement_completed_at || !i.consent_recorded_at)
      .map((i) => action({ key: `agree-${i.id}`, label: `Record agreement: ${i.name}`,
        title: `${i.name}'s agreement and consent`, fields: [
          { name: "agreement_reference", label: "Agreement reference", type: "text",
            required: true },
          { name: "consent", label: "Consent to filing recorded", type: "checkbox" },
        ], submitLabel: "Record" }, agree, (v) => ({ id: app.id, inventorId: i.id,
        agreement_reference: str(v.agreement_reference), consent: Boolean(v.consent) })))
    : [];
  return (
    <Stack gap="sm">
      {app.inventors.length ? (
        <Table>
          <Table.Thead><Table.Tr>
            <Table.Th>Name</Table.Th><Table.Th>Affiliation</Table.Th>
            <Table.Th>Share</Table.Th><Table.Th>Agreement</Table.Th><Table.Th>Consent</Table.Th>
          </Table.Tr></Table.Thead>
          <Table.Tbody>
            {app.inventors.map((i) => (
              <Table.Tr key={i.id}>
                <Table.Td>{i.name}</Table.Td>
                <Table.Td>{i.user_id ? "Institute" : i.affiliation}</Table.Td>
                <Table.Td>{i.share_percent}%</Table.Td>
                <Table.Td>{i.agreement_completed_at ? i.agreement_reference : "Pending"}</Table.Td>
                <Table.Td>{i.consent_recorded_at ? "Recorded" : "Pending"}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : <Text size="sm" c="dimmed">No inventors listed yet.</Text>}
      <Group>
        {owner && can("pms.inventor.update") && EDITABLE.includes(app.status) && (
          <Button size="xs" variant="light" onClick={() => setEditing(true)}>
            Edit inventors
          </Button>
        )}
        <ActionBar actions={actions} />
      </Group>
      {editing && <InventorsModal applicationId={app.id} inventors={app.inventors}
        onClose={() => setEditing(false)} />}
    </Stack>
  );
}

function Documents({ app }: { app: ApplicationDetail }) {
  const can = usePmsCan();
  const docs = h.useDocuments(app.id);
  const download = h.useDownloadVersion();
  const sensitivity = h.useSetSensitivity();
  const [uploading, setUploading] = useState<PmsDocument | "new" | null>(null);
  const rel = new Set(app.relations);
  const mayUpload = can("pms.document.create") && (rel.has("pcc_admin")
    || (rel.has("attorney") && ["attorney_assigned", "filed", "granted"].includes(app.status))
    || (rel.has("applicant") && EDITABLE.includes(app.status)));
  if (docs.isPending) return <Center py="md"><Loader size="sm" /></Center>;
  if (docs.error) return <ErrorState error={docs.error} />;
  return (
    <Stack gap="sm">
      {download.error != null && <ErrorState error={download.error} />}
      {sensitivity.error != null && <ErrorState error={sensitivity.error} />}
      {!docs.data.length && <Text size="sm" c="dimmed">No documents you may read yet.</Text>}
      {docs.data.map((d) => (
        <Stack key={d.id} gap={4} p="sm" style={{ border: "1px solid var(--mantine-color-gray-3)",
          borderRadius: 8 }}>
          <Group justify="space-between">
            <Group gap="xs"><Text fw={600} size="sm">{d.title}</Text>
              <Badge size="xs" variant="light">{words(d.kind)}</Badge>
              <Badge size="xs" color="grape" variant="light">{SENSITIVITY_NAMES[d.sensitivity]}</Badge>
            </Group>
            <Group gap="xs">
              {can("pms.document.update") && (
                <Select size="xs" aria-label={`Sensitivity of ${d.title}`} w={160}
                  value={d.sensitivity}
                  data={Object.entries(SENSITIVITY_NAMES).map(([value, label]) => ({ value, label }))}
                  onChange={(v) => v && v !== d.sensitivity
                    && sensitivity.mutate({ id: d.id, sensitivity: v })} />
              )}
              {mayUpload && (
                <Button size="xs" variant="subtle" onClick={() => setUploading(d)}>
                  New version
                </Button>
              )}
            </Group>
          </Group>
          {d.versions.map((v) => (
            <Group key={v.id} justify="space-between">
              <Text size="xs">Version {v.number}{v.is_current ? " (current)" : " (archived)"} —
                {" "}{v.original_name}, {day(v.uploaded_at)}</Text>
              <Button size="xs" variant="subtle" aria-label={`Download version ${v.number} of ${d.title}`}
                onClick={() => download.mutate({ id: v.id, name: v.original_name })}>
                Download
              </Button>
            </Group>
          ))}
        </Stack>
      ))}
      {mayUpload && (
        <Group><Button size="xs" onClick={() => setUploading("new")}>Upload document</Button></Group>
      )}
      {uploading && <UploadModal applicationId={app.id}
        existing={uploading === "new" ? null : uploading} onClose={() => setUploading(null)} />}
    </Stack>
  );
}

function Decisions({ app }: { app: ApplicationDetail }) {
  return (
    <Stack gap="md">
      <Title order={5}>Review cycles</Title>
      <Rows empty="Not assigned to a Director yet." rows={app.review_cycles.map((c) => [
        `Cycle ${c.cycle_no}: ${c.director_name}`,
        `${words(c.status)}${c.decision ? ` — ${words(c.decision)}` : ""}, due ${c.due_on}`
          + (c.justification ? `\n${c.justification}` : "")])} />
      <Title order={5}>Appeals</Title>
      <Rows empty="No appeal." rows={app.appeals.map((a) => [`Appeal #${a.id}`,
        `${words(a.status)}${a.outcome ? ` — ${words(a.outcome)}` : ""}`
          + `${a.director_name ? `, heard by ${a.director_name}` : ", Director not assigned"}`
          + `\nGrounds: ${a.grounds}${a.outcome_note ? `\n${a.outcome_note}` : ""}`])} />
    </Stack>
  );
}

function Case({ app }: { app: ApplicationDetail }) {
  return (
    <Stack gap="md">
      <Title order={5}>Attorney</Title>
      <Rows empty="No attorney assigned." rows={app.attorney_assignments.map((a) => [
        a.attorney_name, `${words(a.status)}${a.is_exception ? " (institutional exception)" : ""}`
          + (a.decline_reason ? ` — ${a.decline_reason}` : "")])} />
      <Title order={5}>Budget</Title>
      <Rows empty="No budget proposed." rows={app.budgets.map((b) => [`Budget #${b.id}`,
        `${words(b.status)}: ${money(b.total)} (filing ${money(b.filing_fee)}, attorney `
          + `${money(b.attorney_fee)}, administrative ${money(b.admin_cost)})`
          + (b.routed_to ? `\nRouted to ${b.routed_to}` : "")])} />
      <Title order={5}>Patentability opinions</Title>
      <Rows empty="No opinion recorded." rows={app.assessments.map((a) => [
        `${words(a.status)} opinion`, `${a.recommendation ? words(a.recommendation)
          : "No recommendation yet"}`
          + `\n${a.analysis}`])} />
      <Title order={5}>Filings and communications</Title>
      <Rows empty="Not filed yet." rows={[
        ...app.filings.map((f): [string, string] => [`${f.office_name} (${f.jurisdiction})`,
          `${f.external_filing_id}, filed ${f.filing_date}, confirmation ${f.confirmation_reference}`]),
        ...app.communications.map((c): [string, string] => [`${words(c.kind)} ${c.reference}`,
          `Received ${c.received_on}${c.details ? `\n${c.details}` : ""}`]),
      ]} />
      <Title order={5}>Office actions</Title>
      <Rows empty="No office actions." rows={app.office_actions.map((o) => [o.reference,
        `${words(o.status)}, due ${o.current_due_on ?? "not given"}`
          + (o.draft_response ? `\nDraft: ${o.draft_response}` : "")])} />
      <Title order={5}>Maintenance</Title>
      <Rows empty="No maintenance cycles." rows={app.maintenance_cycles.map((c) => [
        `Cycle ${c.seq}, due ${c.due_on}`, `${words(c.status)}`
          + (c.director_name ? `, decided by ${c.director_name}` : "")])} />
      <Title order={5}>Legal advice and requests</Title>
      <Rows empty="None recorded." rows={[
        ...app.legal_requests.map((r): [string, string] => [`Request for ${r.kind}`, r.message]),
        ...app.legal_advice.map((a): [string, string] => [`Advice (${words(a.stage)})`, a.advice]),
      ]} />
    </Stack>
  );
}

function PriorArt({ app }: { app: ApplicationDetail }) {
  const refs = h.usePriorArt(app.id);
  if (refs.isPending) return <Center py="md"><Loader size="sm" /></Center>;
  if (refs.error) return <ErrorState error={refs.error} />;
  return <Rows empty="No prior art attached." rows={refs.data.map((r) => [
    `${words(r.kind)} ${r.identifier}`, `${r.title}${r.notes ? `\n${r.notes}` : ""}`])} />;
}

function History({ app }: { app: ApplicationDetail }) {
  const hist = h.useHistory(app.id);
  if (hist.isPending) return <Center py="md"><Loader size="sm" /></Center>;
  if (hist.error) return <ErrorState error={hist.error} />;
  return <Rows rows={hist.data.map((e) => [day(e.at) + " " + e.at.slice(11, 16),
    `${words(e.action.replace(".", " "))}${e.to_state ? ` → ${words(e.to_state)}` : ""}`])} />;
}

// One application, everything the acting role may see about it, and only the actions it may take.
export function ApplicationDrawer({ id, onClose }: { id: number | null; onClose: () => void }) {
  const detail = h.useApplication(id);
  const actions = useApplicationActions(detail.data);
  return (
    <Drawer opened={id != null} onClose={onClose} position="right" size="xl"
      title={detail.data ? `${detail.data.reference || "Draft"} — ${detail.data.title}`
        : "Application"}>
      {detail.isPending && <Center py="xl"><Loader /></Center>}
      {detail.error != null && <ErrorState error={detail.error} />}
      {detail.data && (
        <Stack gap="md">
          <Group justify="space-between"><StatusBadge status={detail.data.status} /></Group>
          <ActionBar actions={actions} />
          <Tabs defaultValue="overview" keepMounted={false}>
            <Tabs.List>
              <Tabs.Tab value="overview">Overview</Tabs.Tab>
              <Tabs.Tab value="inventors">Inventors</Tabs.Tab>
              <Tabs.Tab value="documents">Documents</Tabs.Tab>
              <Tabs.Tab value="decisions">Decisions</Tabs.Tab>
              <Tabs.Tab value="case">Case</Tabs.Tab>
              <Tabs.Tab value="prior-art">Prior art</Tabs.Tab>
              <Tabs.Tab value="history">History</Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="overview" pt="md"><Overview app={detail.data} /></Tabs.Panel>
            <Tabs.Panel value="inventors" pt="md"><Inventors app={detail.data} /></Tabs.Panel>
            <Tabs.Panel value="documents" pt="md"><Documents app={detail.data} /></Tabs.Panel>
            <Tabs.Panel value="decisions" pt="md"><Decisions app={detail.data} /></Tabs.Panel>
            <Tabs.Panel value="case" pt="md"><Case app={detail.data} /></Tabs.Panel>
            <Tabs.Panel value="prior-art" pt="md"><PriorArt app={detail.data} /></Tabs.Panel>
            <Tabs.Panel value="history" pt="md"><History app={detail.data} /></Tabs.Panel>
          </Tabs>
        </Stack>
      )}
    </Drawer>
  );
}
