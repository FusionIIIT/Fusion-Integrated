import { useState } from "react";
import {
  Alert, Button, Card, Container, Group, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaInfoCircle } from "react-icons/fa";
import { Link } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { usePmsAction, usePmsConfiguration, useAttorneyPanel } from "../api/hooks";
import { PmsActionForm } from "../components/PmsActionForm";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable, type Column } from "../../../ui/components/DataTable";
import type { AttorneyPanelEntry } from "../api/types";

const CONFIG_KEYS = [
  "review_business_days", "revision_days", "alert_offsets", "holiday_calendar",
  "budget_threshold", "appeal_period_days", "escalation_chain", "maintenance_schedule",
];

function PolicyConfiguration() {
  const query = usePmsConfiguration();
  const [key, setKey] = useState(CONFIG_KEYS[0]);
  const [value, setValue] = useState("");
  const [description, setDescription] = useState("");
  const [parseError, setParseError] = useState("");
  const save = usePmsAction("put", () => "/configuration/");
  const remove = usePmsAction("delete", (body) => `/configuration/${encodeURIComponent(String(body.key))}/`);

  function saveValue(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const parsed: unknown = JSON.parse(value);
      setParseError("");
      save.mutate({ key, value: parsed, description }, {
        onSuccess: () => notifications.show({ color: "green", title: "Policy saved", message: `${key} was validated and stored.` }),
      });
    } catch {
      setParseError("Enter a valid JSON value. Numbers are unquoted; lists and objects use JSON brackets/braces.");
    }
  }

  if (query.error) return <ErrorState error={query.error} />;
  return (
    <Stack gap="md">
      <Card withBorder padding="md">
        <form onSubmit={saveValue}>
          <Stack>
            <Text size="sm" c="dimmed">Only existing PMS policy keys are accepted. Values are validated by the server before saving.</Text>
            <select aria-label="Configuration key" value={key} onChange={(event) => setKey(event.currentTarget.value)}>
              {CONFIG_KEYS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
            <Textarea label="Policy value (JSON)" required minRows={3} autosize value={value}
              onChange={(event) => setValue(event.currentTarget.value)} />
            <Textarea label="Description" minRows={2} value={description}
              onChange={(event) => setDescription(event.currentTarget.value)} />
            {parseError && <Alert color="red">{parseError}</Alert>}
            {save.error && <ErrorState error={save.error} />}
            <Button type="submit" loading={save.isPending}>Save policy value</Button>
          </Stack>
        </form>
      </Card>
      <Stack gap="sm">
        {query.isPending && <Text c="dimmed">Loading configured policies…</Text>}
        {(query.data ?? []).map((row) => (
          <Card key={row.key} withBorder padding="md">
            <Group justify="space-between" align="flex-start">
              <div>
                <Text fw={600}>{row.key}</Text>
                <Text size="sm" ff="monospace">{JSON.stringify(row.value)}</Text>
                <Text size="xs" c="dimmed">{row.description}</Text>
              </div>
              <Button color="red" variant="light" loading={remove.isPending}
                onClick={() => remove.mutate({ key: row.key }, {
                  onSuccess: () => notifications.show({ color: "green", title: "Policy removed", message: `${row.key} now uses its specified unset/default behavior.` }),
                })}>
                Remove
              </Button>
            </Group>
          </Card>
        ))}
        {!query.isPending && !query.data?.length && (
          <Alert color="blue" variant="light">No operator policy overrides are configured.</Alert>
        )}
        {remove.error && <ErrorState error={remove.error} />}
      </Stack>
    </Stack>
  );
}

function AttorneyPanelManagement() {
  const panel = useAttorneyPanel();
  const columns: Column<AttorneyPanelEntry>[] = [
    { key: "name", header: "Attorney" },
    { key: "attorney_user_id", header: "IAM user ID" },
    { key: "firm_name", header: "Firm" },
    { key: "expertise_domains", header: "Expertise", render: (row) => row.expertise_domains.join(", ") || "—" },
    { key: "workload", header: "Workload", render: (row) => `${row.current_workload}/${row.max_workload}` },
  ];
  if (panel.error) return <ErrorState error={panel.error} />;
  return (
    <Stack gap="md">
      <DataTable rows={panel.data ?? []} columns={columns} rowKey={(row) => row.id}
        loading={panel.isPending} minWidth={760}
        empty={{ title: "Attorney panel is empty", description: "Add approved panel members below." }} />
      <PmsActionForm
        title="Add panel member"
        path={() => "/attorney-panel/"}
        fields={[
          { name: "attorney_user_id", label: "Attorney IAM user ID", type: "number", required: true },
          { name: "name", label: "Name", required: true },
          { name: "firm_name", label: "Firm" },
          { name: "email", label: "Email", type: "email", required: true },
          { name: "expertise_domains", label: "Expertise domains (comma separated)", required: true },
          { name: "is_approved", label: "Approved panel member", type: "checkbox", initialValue: true },
          { name: "max_workload", label: "Maximum workload", type: "number", initialValue: "10" },
        ]}
        transform={(body) => ({
          ...body,
          attorney_user_id: Number(body.attorney_user_id),
          expertise_domains: String(body.expertise_domains).split(",").map((x) => x.trim()).filter(Boolean),
          max_workload: Number(body.max_workload),
        })}
        submitLabel="Add attorney"
      />
      {(panel.data ?? []).map((entry) => (
        <Card key={entry.id} withBorder padding="md">
          <Text fw={600} mb="sm">Edit {entry.name}</Text>
          <Stack gap="sm">
            <PmsActionForm
              method="patch"
              title="Update panel details"
              path={() => `/attorney-panel/${entry.id}/`}
              fields={[
                { name: "name", label: "Name", initialValue: entry.name },
                { name: "firm_name", label: "Firm", initialValue: entry.firm_name },
                { name: "email", label: "Email", type: "email", initialValue: entry.email },
                { name: "expertise_domains", label: "Expertise domains (comma separated)", initialValue: entry.expertise_domains.join(", ") },
                { name: "is_approved", label: "Approved panel member", type: "checkbox", initialValue: entry.is_approved },
                { name: "max_workload", label: "Maximum workload", type: "number", initialValue: String(entry.max_workload) },
              ]}
              transform={(body) => ({
                ...Object.fromEntries(Object.entries(body).filter(([, value]) => value !== "")),
                expertise_domains: String(body.expertise_domains).split(",").map((x) => x.trim()).filter(Boolean),
                max_workload: Number(body.max_workload),
              })}
              submitLabel="Save panel changes"
              compact
            />
            <PmsActionForm method="delete" title="Remove from panel"
              path={() => `/attorney-panel/${entry.id}/`}
              fields={[]} submitLabel={`Remove ${entry.name}`} compact />
          </Stack>
        </Card>
      ))}
    </Stack>
  );
}

export default function AdminPage() {
  const { can } = useAuth();
  const canConfigure = can("pms.config.manage");
  const canManagePanel = can("pms.panel.manage");
  return (
    <Container size="xl">
      <PageHeader title="PMS administration" subtitle="Manage policy values and attorney panel data using the current PMS permissions." />
      {!canConfigure && !canManagePanel && (
        <Alert color="blue" variant="light" icon={<FaInfoCircle />}>
          IAM role grants are managed through the platform IAM system. PMS does not expose a role-assignment endpoint.
        </Alert>
      )}
      {(can("pms.workflow.monitor") || can("pms.workflow.oversight")) && (
        <Alert color="blue" variant="light" mb="md">
          Workflow exception and pending-action visibility: <Link to="../oversight">Open workflow oversight</Link>.
        </Alert>
      )}
      {canConfigure && <Card padding="lg" mb="md"><PageHeader title="Policy configuration" /><PolicyConfiguration /></Card>}
      {canManagePanel && <Card padding="lg"><PageHeader title="Attorney panel" /><AttorneyPanelManagement /></Card>}
      <Alert color="blue" variant="light" mt="md" icon={<FaInfoCircle />}>
        This administration screen does not change IAM roles or permissions. The API validates all configuration and panel changes.
      </Alert>
    </Container>
  );
}
