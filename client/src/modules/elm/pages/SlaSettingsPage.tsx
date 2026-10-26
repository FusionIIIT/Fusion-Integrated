import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useMemo, useState } from "react";
import { FaBell, FaExclamationTriangle, FaPlay } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useSlaConfigurationMutation,
  useSlaConfigurations,
  useSlaEvents,
  useSlaProcessMutation,
} from "../api/hooks";
import { TASK_KINDS, type SlaConfigurationInput, type TaskKind } from "../api/types";

const KIND_LABELS: Record<TaskKind, string> = {
  SUBSTITUTE_RESPONSE: "Substitute response",
  UNIT_HEAD_REVIEW: "Unit Head review",
  ESTABLISHMENT_ROUTING: "Establishment routing",
  SANCTION_DECISION: "Sanction decision",
  DIRECTOR_SELF_SANCTION: "Director self-sanction",
  CANCELLATION_UNIT_HEAD: "Cancellation — Unit Head",
  CANCELLATION_SANCTION: "Cancellation — sanction",
  EXTENSION_UNIT_HEAD: "Extension — Unit Head",
  EXTENSION_SANCTION: "Extension — sanction",
  RESUMPTION_REVIEW: "Resumption review",
};

/** Reason codes from modules/elm/domain/sla.py SlaReason, in plain words. */
const REASON_LABELS: Record<string, string> = {
  task_not_pending: "Already actioned — suppressed",
  sla_not_configured: "No thresholds configured",
  sla_config_inactive: "Thresholds inactive",
  below_reminder_threshold: "Within threshold",
  reminder_threshold_reached: "Reminder issued",
  reminder_already_issued: "Reminder already sent",
  escalation_threshold_passed: "Escalation issued",
  escalation_already_issued: "Escalation already sent",
};

type Draft = SlaConfigurationInput & { error?: string };

function emptyDraft(kind: TaskKind): Draft {
  return {
    task_kind: kind,
    reminder_hours: 24,
    escalation_hours: 48,
    escalation_role: "",
    escalation_recipient_id: null,
    escalation_changes_routing: false,
    is_active: true,
  };
}

export default function SlaSettingsPage() {
  const { data: configs = [], isLoading } = useSlaConfigurations();
  const { data: events = [] } = useSlaEvents();
  const save = useSlaConfigurationMutation();
  const run = useSlaProcessMutation();

  const [drafts, setDrafts] = useState<Record<string, Draft>>({});

  const rows = useMemo(() => {
    const byKind = new Map(configs.map((c) => [String(c.task_kind), c]));
    return TASK_KINDS.map((kind) => {
      const existing = byKind.get(kind);
      const draft =
        drafts[kind] ??
        (existing
          ? {
              task_kind: kind,
              reminder_hours: Number(existing.reminder_hours),
              escalation_hours: Number(existing.escalation_hours),
              escalation_role: existing.escalation_role,
              escalation_recipient_id: existing.escalation_recipient_id,
              escalation_changes_routing: existing.escalation_changes_routing,
              is_active: existing.is_active,
            }
          : emptyDraft(kind));
      return { kind, existing, draft };
    });
  }, [configs, drafts]);

  function update(kind: TaskKind, patch: Partial<Draft>) {
    setDrafts((prev) => ({
      ...prev,
      [kind]: { ...(prev[kind] ?? emptyDraft(kind)), ...patch, error: undefined },
    }));
  }

  function onSave(kind: TaskKind, draft: Draft) {
    // Mirrors SlaThresholds.validate() so the obvious mistake is caught before
    // a round trip. The server still re-checks: the domain is the authority.
    if (draft.escalation_hours <= draft.reminder_hours) {
      update(kind, { error: "Escalation must be later than the reminder." });
      return;
    }
    if (draft.escalation_changes_routing && !draft.escalation_recipient_id) {
      update(kind, { error: "A rerouting escalation needs a recipient user id." });
      return;
    }
    save.mutate(draft, {
      onError: (err: unknown) => {
        const detail =
          (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data
            ?.error?.message ?? "Could not save.";
        update(kind, { error: detail });
      },
    });
  }

  return (
    <div>
      <PageHeader
        title="SLA Settings"
        subtitle="Reminder and escalation thresholds for actionable leave tasks (BR-EL-032, BR-EL-033, BR-EL-038)"
      />

      <Alert
        icon={<FaBell size={14} />}
        color="gray"
        variant="light"
        mb="md"
        title="How these are applied"
      >
        <Text size="sm">
          Thresholds are measured in hours from the moment a task lands on its current assignee.
          A reminder goes to that assignee; an escalation goes to the authority configured below.
          A task that has already been actioned is never reminded or escalated, however overdue
          it looks.
        </Text>
      </Alert>

      <Group justify="space-between" mb="sm">
        <Title order={4}>Thresholds by task</Title>
        <Button
          leftSection={<FaPlay size={12} />}
          variant="light"
          loading={run.isPending}
          onClick={() => run.mutate(undefined)}
        >
          Run SLA pass now
        </Button>
      </Group>

      {run.data && (
        <Alert color="blue" variant="light" mb="md">
          <Text size="sm">
            {run.data.evaluated} task(s) evaluated — {run.data.reminded} reminded,{" "}
            {run.data.escalated} escalated ({run.data.rerouted} rerouted),{" "}
            {run.data.suppressed} suppressed.
          </Text>
        </Alert>
      )}

      <Stack gap="sm">
        {rows.map(({ kind, existing, draft }) => (
          <Card key={kind} withBorder padding="md" radius="md">
            <Group justify="space-between" mb="xs">
              <Group gap="xs">
                <Text fw={600}>{KIND_LABELS[kind]}</Text>
                {existing ? (
                  draft.is_active ? (
                    <Badge color="green" variant="light">Active</Badge>
                  ) : (
                    <Badge color="gray" variant="light">Inactive</Badge>
                  )
                ) : (
                  <Badge color="orange" variant="light">Not configured</Badge>
                )}
              </Group>
              <Switch
                label="Active"
                checked={Boolean(draft.is_active)}
                onChange={(e) => update(kind, { is_active: e.currentTarget.checked })}
              />
            </Group>

            <Group align="flex-end" gap="md" wrap="wrap">
              <NumberInput
                label="Remind after (hours)"
                min={0.5}
                step={1}
                w={170}
                value={draft.reminder_hours}
                onChange={(v) => update(kind, { reminder_hours: Number(v) || 0 })}
              />
              <NumberInput
                label="Escalate after (hours)"
                min={0.5}
                step={1}
                w={180}
                value={draft.escalation_hours}
                onChange={(v) => update(kind, { escalation_hours: Number(v) || 0 })}
              />
              <TextInput
                label="Escalate to (role label)"
                placeholder="Registrar"
                w={200}
                value={draft.escalation_role ?? ""}
                onChange={(e) => update(kind, { escalation_role: e.currentTarget.value })}
              />
              <NumberInput
                label="Escalate to (user id)"
                description="Who actually receives it"
                min={1}
                w={180}
                value={draft.escalation_recipient_id ?? ""}
                onChange={(v) =>
                  update(kind, { escalation_recipient_id: v === "" ? null : Number(v) })
                }
              />
              <Switch
                mb={6}
                label="Escalation reassigns the task"
                checked={Boolean(draft.escalation_changes_routing)}
                onChange={(e) =>
                  update(kind, { escalation_changes_routing: e.currentTarget.checked })
                }
              />
              <Button
                mb={4}
                loading={save.isPending}
                onClick={() => onSave(kind, draft)}
              >
                Save
              </Button>
            </Group>

            {draft.error && (
              <Alert
                mt="xs"
                color="red"
                variant="light"
                icon={<FaExclamationTriangle size={14} />}
              >
                <Text size="sm">{draft.error}</Text>
              </Alert>
            )}
          </Card>
        ))}
        {isLoading && <Text size="sm" c="dimmed">Loading configuration…</Text>}
      </Stack>

      <Title order={4} mt="xl" mb="sm">
        Recent SLA events
      </Title>
      <Text size="sm" c="dimmed" mb="xs">
        Suppressed evaluations are listed too, so a task that was deliberately not reminded is
        visible rather than silent.
      </Text>
      <Card withBorder padding={0} radius="md">
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>When</Table.Th>
              <Table.Th>Task</Table.Th>
              <Table.Th>Kind</Table.Th>
              <Table.Th>Action</Table.Th>
              <Table.Th>Outcome</Table.Th>
              <Table.Th>Waited</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {events.map((e) => (
              <Table.Tr key={e.id}>
                <Table.Td>{new Date(e.evaluated_at).toLocaleString()}</Table.Td>
                <Table.Td>#{e.task_id}</Table.Td>
                <Table.Td>{KIND_LABELS[e.task_kind as TaskKind] ?? e.task_kind}</Table.Td>
                <Table.Td>
                  <Badge
                    variant="light"
                    color={
                      e.action === "ESCALATE" ? "red" : e.action === "REMIND" ? "yellow" : "gray"
                    }
                  >
                    {e.action}
                  </Badge>
                </Table.Td>
                <Table.Td>{REASON_LABELS[e.reason] ?? e.reason}</Table.Td>
                <Table.Td>{Number(e.hours_elapsed).toFixed(0)} h</Table.Td>
              </Table.Tr>
            ))}
            {events.length === 0 && (
              <Table.Tr>
                <Table.Td colSpan={6}>
                  <Text size="sm" c="dimmed" ta="center" py="md">
                    No SLA events recorded yet.
                  </Text>
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </div>
  );
}
