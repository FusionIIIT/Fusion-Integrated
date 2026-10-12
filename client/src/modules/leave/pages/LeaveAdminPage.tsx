import { useState } from "react";
import { Button, Card, Container, Group, Stack, Tabs, Text } from "@mantine/core";
import { FaClipboardList, FaFileSignature, FaHistory } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveConfig, useLeaveHierarchy, useLeaveSla } from "../api/hooks";

export default function LeaveAdminPage() {
  const config = useLeaveConfig();
  const hierarchy = useLeaveHierarchy();
  const sla = useLeaveSla();
  const [tab, setTab] = useState<"policy" | "hierarchy" | "calendar" | "sla">("policy");

  if (config.error || hierarchy.error || sla.error) {
    return <Container size="xl"><ErrorState error={
      config.error ?? hierarchy.error ?? sla.error
    } /></Container>;
  }

  const tabSection = (tab: "policy" | "hierarchy" | "calendar" | "sla") => {
    switch (tab) {
      case "policy": {
        const c = config.data ?? { periods: [], categories: [] };
        return <DataTable<{ key: string; label: string; value: string }>
          rows={[
            { key: "policy_version", label: "Policy version", value: c.periods.map((p) => p.name).join(", ") },
            { key: "start_date", label: "Academic year start", value: c.periods.map((p) => p.period_from).join(", ") },
            { key: "end_date", label: "Academic year end", value: c.periods.map((p) => p.period_to).join(", ") },
            { key: "categories", label: "Categories", value: c.categories.join(", ") },
          ]}
          loading={config.isPending}
          rowKey={(r) => r.key}
          minWidth={400}
          empty={{ icon: FaClipboardList, title: "No configuration yet", description: "Configure the leave module policies here." }}
          columns={[
            { key: "label", header: "Setting", render: (r) => <Text fw={600}>{r.label}</Text> },
            { key: "value", header: "Value", render: (r) => <Text size="sm">{r.value}</Text> },
          ]}
        />;
      }
      case "hierarchy": {
        const h = hierarchy.data ?? { departments: [], posts: [], committee: [] };
        return <DataTable<{ key: string; label: string; value: string }>
          rows={[
            { key: "departments", label: "Departments", value: h.departments.map((d) => `${d.code} → ${d.manages_of} managers`).join(", ") },
            { key: "posting_types", label: "Posting types", value: h.posts.join(", ") },
            { key: "committee", label: "Leave committee", value: h.committee.join(", ") },
          ]}
          loading={hierarchy.isPending}
          rowKey={(r) => r.key}
          minWidth={400}
          empty={{ icon: FaHistory, title: "No hierarchy yet", description: "Configure the leave module hierarchy here." }}
          columns={[
            { key: "label", header: "Setting", render: (r) => <Text fw={600}>{r.label}</Text> },
            { key: "value", header: "Value", render: (r) => <Text size="sm">{r.value}</Text> },
          ]}
        />;
      }
      case "calendar": {
        const c = config.data ?? { periods: [] };
        return <DataTable<{ name: string; from: string; to: string; note: string }>
          rows={c.periods.map((p) => ({
            name: p.name, from: p.period_from, to: p.period_to, note: p.note ?? "",
          }))}
          loading={config.isPending}
          rowKey={(r) => r.from}
          minWidth={500}
          empty={{ icon: FaClipboardList, title: "No calendar yet", description: "Add academic calendar periods for the leave module." }}
          columns={[
            { key: "name", header: "Period", render: (r) => <Text size="sm">{r.name}</Text> },
            { key: "from", header: "From", render: (r) => r.from },
            { key: "to", header: "To", render: (r) => r.to },
            { key: "note", header: "Note", render: (r) => r.note },
          ]}
        />;
      }
      case "sla": {
        const s = sla.data ?? { targets: [], remind_before: "", escalate_after: "", breach_days: "", lock_after: "" };
        return <DataTable<{ key: string; label: string; value: string }>
          rows={[
            { key: "targets", label: "Targets", value: s.targets.join(", ") },
            { key: "remind_before", label: "Remind before", value: s.remind_before },
            { key: "escalate_after", label: "Escalate after", value: s.escalate_after },
            { key: "breach_days", label: "Breach days", value: s.breach_days },
            { key: "lock_after", label: "Lock after", value: s.lock_after },
          ]}
          loading={sla.isPending}
          rowKey={(r) => r.key}
          minWidth={400}
          empty={{ icon: FaFileSignature, title: "No SLA thresholds yet", description: "Configure leave request SLA windows here." }}
          columns={[
            { key: "label", header: "Setting", render: (r) => <Text fw={600}>{r.label}</Text> },
            { key: "value", header: "Value", render: (r) => <Text size="sm">{r.value}</Text> },
          ]}
        />;
      }
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Administration"
        subtitle="Configure policy, hierarchy, calendar and service levels"
        action={
          <Group gap="sm">
            <Button variant="default" size="xs">Import</Button>
            <Button variant="light" size="xs" color="gray">Export</Button>
          </Group>
        }
      />

      <Group justify="space-between" mb="md">
        <Stack gap={0}>
          <Text fw={600}>Configuration</Text>
          <Text size="sm" c="dimmed">Administer the leave module</Text>
        </Stack>
        <Tabs value={tab} onChange={(v) => setTab(v as never)}>
          <Tabs.List>
            <Tabs.Tab value="policy" leftSection={<FaFileSignature size={12} />}>Policy</Tabs.Tab>
            <Tabs.Tab value="hierarchy" leftSection={<FaHistory size={12} />}>Hierarchy</Tabs.Tab>
            <Tabs.Tab value="calendar" leftSection={<FaClipboardList size={12} />}>Calendar</Tabs.Tab>
            <Tabs.Tab value="sla" leftSection={<FaFileSignature size={12} />}>SLA</Tabs.Tab>
          </Tabs.List>
        </Tabs>
      </Group>

      <Card withBorder padding="lg">
        {tabSection(tab)}
      </Card>
    </Container>
  );
}
