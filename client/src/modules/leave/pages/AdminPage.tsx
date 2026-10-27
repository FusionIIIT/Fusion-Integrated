import { useState } from "react";
import {
  Alert, Badge, Button, Container, Group, NumberInput, Stack, Switch, Table,
  Tabs, Text, TextInput, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaExclamationTriangle, FaPlus, FaSettings2 } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useAdminConfig, useSaveRoute, useSaveThreshold, useSaveUnit, useUpdatePolicy,
} from "../api/hooks";
import { CATEGORY_LABELS, LEAVE_CATEGORIES } from "../api/types";

/** EL-UC-014 / BR-EL-030: the current configuration, edited in place.
 *
 *  There is no draft/publish cycle for policy — the specification forbids one.
 *  The calendar screen, which IS effective-dated, is separate for that reason. */
export default function AdminPage() {
  const config = useAdminConfig();
  const updatePolicy = useUpdatePolicy();
  const saveUnit = useSaveUnit();
  const saveRoute = useSaveRoute();
  const saveThreshold = useSaveThreshold();

  const [unitName, setUnitName] = useState("");
  const [unitHead, setUnitHead] = useState<number | null>(null);
  const [routeName, setRouteName] = useState("");
  const [routeCategory, setRouteCategory] = useState<string>("");
  const [routeUnit, setRouteUnit] = useState<number | null>(null);
  const [thresholdKind, setThresholdKind] = useState<string>("final_sanction");
  const [reminderHours, setReminderHours] = useState<number | null>(24);
  const [escalateHours, setEscalateHours] = useState<number | null>(72);

  if (config.isError) {
    return <Container size="lg"><ErrorState error={config.error} /></Container>;
  }

  const data = config.data;
  const policy = data?.policy;
  const gaps = data?.unassigned_steps ?? [];

  function patch(body: Record<string, unknown>, label: string) {
    updatePolicy.mutate(body as never, {
      onSuccess: () => notifications.show({
        color: "green", title: "Policy updated", message: `${label} saved.`,
      }),
      onError: (e) => notifications.show({
        color: "red", title: "Could not update policy",
        message: errorMessage(e),
      }),
    });
  }

  return (
    <Container size="xl">
      <PageHeader title="Leave Administration"
                   subtitle="Policy, hierarchy and SLA thresholds" />
      {!!gaps.length && (
        <Alert color="orange" variant="light" mb="lg" icon={<FaExclamationTriangle />}>
          <Text fw={600} size="sm">Configuration gaps</Text>
          <Text size="sm">{gaps.join("; ")}</Text>
          <Text size="xs" mt={4}>
            A request cannot be routed to a step that has nobody assigned.
          </Text>
        </Alert>
      )}

      <Tabs defaultValue="policy">
        <Tabs.List mb="md">
          <Tabs.Tab value="policy" leftSection={<FaSettings2 />}>Policy</Tabs.Tab>
          <Tabs.Tab value="units">Units</Tabs.Tab>
          <Tabs.Tab value="routes">Routing</Tabs.Tab>
          <Tabs.Tab value="sla">SLA</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="policy">
          <Stack>
            <FormSection title="Entitlements">
              <Group grow>
                {(["casual_days", "restricted_holiday_days",
                   "special_casual_days", "earned_days", "commuted_days",
                   "vacation_days"] as const).map((field) => (
                  <NumberInput
                    key={field}
                    label={field.replace(/_/g, " ")}
                    value={Number(policy?.[field] ?? 0)}
                    onChange={(v) => patch({ [field]: String(v ?? 0) },
                                           field.replace(/_/g, " "))}
                    min={0} decimalScale={2}
                  />
                ))}
              </Group>
              <NumberInput
                label="Vacation to Earned ratio"
                description="2 Vacation Leave converts to 1 Earned Leave."
                value={Number(policy?.vacation_to_earned_ratio ?? 2)}
                onChange={(v) => patch({ vacation_to_earned_ratio: String(v ?? 2) },
                                       "ratio")}
                min={1} decimalScale={2}
              />
            </FormSection>

            <FormSection title="Carry forward">
              <Stack gap="xs">
                <Switch
                  label="Earned Leave carries forward"
                  checked={policy?.earned_carries_forward ?? true}
                  onChange={(e) => patch(
                    { earned_carries_forward: e.currentTarget.checked },
                    "Earned carry-forward")}
                />
                <Switch
                  label="Commuted Leave carries forward"
                  checked={policy?.commuted_carries_forward ?? true}
                  onChange={(e) => patch(
                    { commuted_carries_forward: e.currentTarget.checked },
                    "Commuted carry-forward")}
                />
                <Alert color="gray" variant="light">
                  The specification states that leave carries forward but names no
                  ceiling, so the caps stay empty until an administrator sets one.
                  Empty means no cap.
                </Alert>
                <Group grow>
                  <NumberInput label="Earned cap (blank = no cap)"
                               value={policy?.earned_carry_forward_cap ?? ""}
                               onChange={(v) => patch(
                                 { earned_carry_forward_cap: v === "" ? null : String(v) },
                                 "Earned cap")}
                               min={0} decimalScale={2} />
                  <NumberInput label="Commuted cap (blank = no cap)"
                               value={policy?.commuted_carry_forward_cap ?? ""}
                               onChange={(v) => patch(
                                 { commuted_carry_forward_cap: v === "" ? null : String(v) },
                                 "Commuted cap")}
                               min={0} decimalScale={2} />
                </Group>
              </Stack>
            </FormSection>

            <FormSection title="Routing">
              <Switch
                label="Establishment step is enabled"
                description="When off, higher-sanction leave goes from the Unit Head to the Sanctioning Authority directly."
                checked={policy?.establishment_step_enabled ?? false}
                onChange={(e) => patch(
                  { establishment_step_enabled: e.currentTarget.checked },
                  "Establishment step")}
              />
              <Text size="sm">
                A substitute is required for:{" "}
                {(policy?.substitute_required_for ?? []).join(", ") || "none configured"}.
              </Text>
            </FormSection>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="units">
          <Stack>
            <FormSection title="Add or update a unit"
                         subtitle="A unit is a department, section or office.">
              <Group align="flex-end">
                <TextInput label="Unit name" value={unitName}
                           onChange={(e) => setUnitName(e.currentTarget.value)} />
                <NumberInput label="Unit Head (user id)" value={unitHead}
                             onChange={setUnitHead} />
                <Button leftSection={<FaPlus />}
                        onClick={() => saveUnit.mutate(
                          { name: unitName.trim(), head_user_id: unitHead },
                          { onSuccess: () => setUnitName(""),
                            onError: (e) => notifications.show({
                              color: "red", title: "Could not save",
                              message: errorMessage(e) }) })}>
                  Save
                </Button>
              </Group>
            </FormSection>
            <Table striped withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Unit</Table.Th>
                  <Table.Th>Unit Head</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(data?.units ?? []).map((u) => (
                  <Table.Tr key={u.id}>
                    <Table.Td>{u.name}</Table.Td>
                    <Table.Td>{u.head_user_id ?? <Badge color="orange">unassigned</Badge>}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="routes">
          <Stack>
            <FormSection title="A route"
                         subtitle="An ordered chain of steps for a leave type, optionally specific to one unit.">
              <Group align="flex-end" grow>
                <TextInput label="Route name" value={routeName}
                           onChange={(e) => setRouteName(e.currentTarget.value)} />
                <TextInput label="Leave type (blank = all)" value={routeCategory}
                           onChange={(e) => setRouteCategory(e.currentTarget.value)} />
                <NumberInput label="Unit id (blank = all)" value={routeUnit}
                             onChange={setRouteUnit} />
              </Group>
              <Button onClick={() => saveRoute.mutate({
                name: routeName.trim(),
                leave_category: LEAVE_CATEGORIES.includes(
                  routeCategory as never) ? routeCategory : "",
                org_unit_id: routeUnit,
                steps: [
                  { kind: "unit_head", designation: "Unit Head" },
                  { kind: "establishment", designation: "Deputy Registrar (Estt.)" },
                  { kind: "final_sanction", designation: "Sanctioning Authority" },
                ],
              }, { onSuccess: () => notifications.show({
                color: "green", title: "Route saved",
                message: "Assign a person to each step to complete it." }),
                onError: (e) => notifications.show({
                  color: "red", title: "Could not save the route",
                  message: errorMessage(e) }) })}>
                Save route
              </Button>
            </FormSection>
            <Table striped withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Route</Table.Th>
                  <Table.Th>Type</Table.Th>
                  <Table.Th>Steps</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(data?.routes ?? []).map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>{r.name}</Table.Td>
                    <Table.Td>
                      {r.leave_category
                        ? CATEGORY_LABELS[r.leave_category] ?? r.leave_category
                        : "All"}
                    </Table.Td>
                    <Table.Td>
                      <Group gap={4}>
                        {r.steps.map((s) => (
                          <Badge key={s.id} variant="light"
                                 color={s.user_id ? "gray" : "orange"}>
                            {s.designation || s.kind}
                            {s.user_id ? ` → ${s.user_id}` : " (unassigned)"}
                          </Badge>
                        ))}
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="sla">
          <Stack>
            <FormSection title="Thresholds"
                         subtitle="How long a task may sit before a reminder, and before an escalation.">
              <Group align="flex-end">
                <TextInput label="Task kind" value={thresholdKind}
                           onChange={(e) => setThresholdKind(e.currentTarget.value)} />
                <NumberInput label="Remind after (hours)" value={reminderHours}
                             onChange={setReminderHours} min={1} />
                <NumberInput label="Escalate after (hours)" value={escalateHours}
                             onChange={setEscalateHours} min={1} />
                <Button onClick={() => saveThreshold.mutate({
                  task_kind: thresholdKind,
                  reminder_hours: reminderHours,
                  escalate_hours: escalateHours,
                }, { onSuccess: () => notifications.show({
                  color: "green", title: "Threshold saved" }),
                  onError: (e) => notifications.show({
                    color: "red", title: "Could not save",
                    message: errorMessage(e) }) })}>
                  Save
                </Button>
              </Group>
            </FormSection>
            <Title order={6}>Configured thresholds</Title>
            <Table striped withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Task kind</Table.Th>
                  <Table.Th>Remind</Table.Th>
                  <Table.Th>Escalate</Table.Th>
                  <Table.Th>Moves routing</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {(data?.thresholds ?? []).map((t) => (
                  <Table.Tr key={t.id}>
                    <Table.Td>{t.task_kind.replace(/_/g, " ")}</Table.Td>
                    <Table.Td>{t.reminder_hours ? `${t.reminder_hours}h` : "—"}</Table.Td>
                    <Table.Td>{t.escalate_hours ? `${t.escalate_hours}h` : "—"}</Table.Td>
                    <Table.Td>{t.escalation_changes_routing ? "Yes" : "No"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}