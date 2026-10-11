import {
  Card, Container, Group, Stack, Table, Text, Title,
} from "@mantine/core";
import { useQuery } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";

interface PolicyRow {
  entitlements: Record<string, {
    annual_days?: string; carry_forward?: boolean; half_day?: boolean;
  }>;
  year_end_month_day: string;
  station_leave_enabled: boolean;
  medical_evidence_required: boolean;
}

interface HierarchyRow {
  category_group: string; unit_type: string;
  establishment_required: boolean; sanctioning_authority: string;
}

interface SlaRow {
  task_class: string; reminder_hours: number; escalation_hours: number;
  escalation_action: string; escalation_target_role: string;
}

export default function ConfigPage() {
  const policy = useQuery({
    queryKey: ["elm", "admin", "policy"],
    queryFn: async () => (await http.get<PolicyRow>("/elm/admin/policy")).data,
  });
  const hierarchy = useQuery({
    queryKey: ["elm", "admin", "hierarchy"],
    queryFn: async () => (await http.get<HierarchyRow[]>("/elm/admin/hierarchy")).data,
  });
  const sla = useQuery({
    queryKey: ["elm", "admin", "sla"],
    queryFn: async () => (await http.get<SlaRow[]>("/elm/admin/sla")).data,
  });

  if (policy.error) return <Container size="xl"><ErrorState error={policy.error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Configuration"
        subtitle="Entitlements, the sanctioning hierarchy and SLA thresholds"
      />
      <Stack>
        <Card withBorder radius="md" p="md">
          <Title order={4} mb="sm">Policy parameters</Title>
          {policy.data ? (
            <Table>
              <Table.Tbody>
                {Object.entries(policy.data.entitlements).map(([category, rules]) => (
                  <Table.Tr key={category}>
                    <Table.Td><b>{category}</b></Table.Td>
                    <Table.Td>{rules.annual_days ?? "?"} days/year</Table.Td>
                    <Table.Td>
                      {rules.carry_forward ? "carries forward" : "lapses"}
                      {rules.half_day ? " · half-day supported" : ""}
                    </Table.Td>
                  </Table.Tr>
                ))}
                <Table.Tr>
                  <Table.Td>Year-end boundary</Table.Td>
                  <Table.Td colSpan={2}>{policy.data.year_end_month_day}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>Station leave</Table.Td>
                  <Table.Td colSpan={2}>
                    {policy.data.station_leave_enabled ? "enabled" : "disabled"}
                  </Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td>COL evidence</Table.Td>
                  <Table.Td colSpan={2}>
                    {policy.data.medical_evidence_required ? "required" : "optional"}
                  </Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
          ) : <Text c="dimmed">Loading…</Text>}
        </Card>

        <Card withBorder radius="md" p="md">
          <Title order={4} mb="sm">Sanctioning hierarchy</Title>
          {hierarchy.data ? (
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Category group</Table.Th>
                  <Table.Th>Unit type</Table.Th>
                  <Table.Th>Establishment</Table.Th>
                  <Table.Th>Sanctioning authority</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {hierarchy.data.map((row) => (
                  <Table.Tr key={`${row.category_group}-${row.unit_type}`}>
                    <Table.Td>{row.category_group}</Table.Td>
                    <Table.Td>{row.unit_type}</Table.Td>
                    <Table.Td>{row.establishment_required ? "yes" : "no"}</Table.Td>
                    <Table.Td>{row.sanctioning_authority}</Table.Td>
                  </Table.Tr>
                ))}
                {hierarchy.data.length === 0 && (
                  <Table.Tr><Table.Td colSpan={4}>No hierarchy configured yet.</Table.Td></Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          ) : <Text c="dimmed">Loading…</Text>}
        </Card>

        <Card withBorder radius="md" p="md">
          <Title order={4} mb="sm">SLA thresholds</Title>
          {sla.data ? (
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Task class</Table.Th>
                  <Table.Th>Reminder after</Table.Th>
                  <Table.Th>Escalation after</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {sla.data.map((row) => (
                  <Table.Tr key={row.task_class}>
                    <Table.Td>{row.task_class}</Table.Td>
                    <Table.Td>{row.reminder_hours}h</Table.Td>
                    <Table.Td>{row.escalation_hours}h</Table.Td>
                    <Table.Td>
                      {row.escalation_action}
                      {row.escalation_target_role ? ` → ${row.escalation_target_role}` : ""}
                    </Table.Td>
                  </Table.Tr>
                ))}
                {sla.data.length === 0 && (
                  <Table.Tr><Table.Td colSpan={4}>No SLA rows configured yet.</Table.Td></Table.Tr>
                )}
              </Table.Tbody>
            </Table>
          ) : <Text c="dimmed">Loading…</Text>}
        </Card>

        <Card withBorder radius="md" p="md">
          <Group justify="space-between">
            <Title order={4}>Records maintenance & year-end</Title>
          </Group>
          <Text size="sm" c="dimmed">
            These are deliberate POST actions from an admin console — use the
            API client or the leave office's tooling. They are guarded by
            `elm.records.maintain`, `elm.yearend.run` and `elm.config.calendar`.
          </Text>
        </Card>
      </Stack>
    </Container>
  );
}
