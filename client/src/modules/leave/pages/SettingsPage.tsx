import { Container, SimpleGrid, Tabs } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useAuthorityRules, usePolicies, useUnits } from "../api/hooks";
import type { AuthorityRule, Policy, Unit } from "../api/types";
import { AdminForm } from "../components/AdminForm";

const CATS = ["CL", "RH", "SCL", "EL", "COL", "VL"];
const STATES = ["awaiting_substitute", "applicant_action_required", "awaiting_unit_head",
  "awaiting_establishment", "awaiting_final_decision"];

/** EL-UC-014 and EL-UC-018: current configuration, used as soon as it is saved. */
export default function SettingsPage() {
  const policies = usePolicies();
  const units = useUnits();
  const rules = useAuthorityRules();
  const error = policies.error ?? units.error ?? rules.error;
  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader title="Leave Settings"
        subtitle="Policy, hierarchy and SLA. Changes apply to the next action taken." />
      <Tabs defaultValue="policy">
        <Tabs.List mb="md">
          <Tabs.Tab value="policy">Policy</Tabs.Tab>
          <Tabs.Tab value="hierarchy">Hierarchy</Tabs.Tab>
          <Tabs.Tab value="sla">SLA</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="policy">
          <AdminForm title="Set a category's policy" method="put" path="/leave/settings/policies"
            fields={[{ name: "category", label: "Category", type: "select", options: CATS },
              { name: "annual_days", label: "Days per year", type: "number" },
              { name: "requires_substitute", label: "Substitute required", type: "select",
                options: ["no", "yes"] },
              { name: "max_days_per_request", label: "Max days per request", type: "number",
                optional: true }]}
            transform={(v) => ({ ...v, requires_substitute: v.requires_substitute === "yes" })} />
          <DataTable<Policy> rows={policies.data ?? []} loading={policies.isPending}
            rowKey={(p) => p.category} empty={{ title: "No policy configured",
              description: "Employees cannot apply until each category has a policy." }}
            columns={[{ key: "category", header: "Category" },
              { key: "annual_days", header: "Days/year" },
              { key: "requires_substitute", header: "Substitute",
                render: (p) => (p.requires_substitute ? "Required" : "Optional") },
              { key: "max_days_per_request", header: "Max/request",
                render: (p) => p.max_days_per_request ?? "—" }]} />
        </Tabs.Panel>

        <Tabs.Panel value="hierarchy">
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <AdminForm title="Unit and its head" path="/leave/settings/units"
              fields={[{ name: "name", label: "Unit (department name)" },
                { name: "head_user_id", label: "Unit Head user id", type: "number" },
                { name: "parent_name", label: "Parent unit", optional: true }]} />
            <AdminForm title="Director" method="put" path="/leave/settings/director"
              fields={[{ name: "user_id", label: "Director user id", type: "number" }]} />
          </SimpleGrid>
          <AdminForm title="Sanctioning route (SCL/EL/COL/VL)"
            path="/leave/settings/authority-rules"
            fields={[{ name: "category", label: "Category", type: "select",
              options: ["SCL", "EL", "COL", "VL"] },
              { name: "unit_name", label: "Unit (blank = all)", optional: true },
              { name: "applicant_kind", label: "Applicant kind", type: "select",
                options: ["faculty", "staff"], optional: true },
              { name: "sanctioning_user_id", label: "Sanctioning authority id", type: "number" },
              { name: "establishment_user_id", label: "Establishment id (optional)",
                type: "number", optional: true }]} />
          <DataTable<Unit> rows={units.data ?? []} loading={units.isPending} rowKey={(u) => u.id}
            empty={{ title: "No units configured" }}
            columns={[{ key: "name", header: "Unit" },
              { key: "head_user_id", header: "Head" },
              { key: "parent_name", header: "Parent", render: (u) => u.parent_name || "—" }]} />
          <DataTable<AuthorityRule> rows={rules.data ?? []} loading={rules.isPending}
            rowKey={(r) => r.id} empty={{ title: "No sanctioning routes configured" }}
            columns={[{ key: "category", header: "Category" },
              { key: "unit_name", header: "Unit", render: (r) => r.unit_name || "Any" },
              { key: "applicant_kind", header: "Kind", render: (r) => r.applicant_kind || "Any" },
              { key: "establishment_user_id", header: "Establishment",
                render: (r) => r.establishment_user_id ?? "Skipped" },
              { key: "sanctioning_user_id", header: "Sanctions" }]} />
        </Tabs.Panel>

        <Tabs.Panel value="sla">
          <AdminForm title="Reminder and escalation thresholds" method="put"
            path="/leave/settings/sla"
            fields={[{ name: "state", label: "Waiting at", type: "select", options: STATES },
              { name: "reminder_hours", label: "Remind after (hours)", type: "number" },
              { name: "escalation_hours", label: "Escalate after (hours)", type: "number" },
              { name: "escalate_to_user_id", label: "Escalate to user id", type: "number",
                optional: true }]} />
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}
