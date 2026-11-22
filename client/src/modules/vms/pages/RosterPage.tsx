import { useState } from "react";
import {
  Badge, Button, Card, Container, Group, SimpleGrid, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaListAlt } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDashboard, useOnSite, useTerminatePass } from "../api/hooks";
import type { OnSiteVisitor } from "../api/types";
import { formatDateTime } from "../format";

function Stat({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <Card withBorder padding="md">
      <Text size="xs" c="dimmed">{label}</Text>
      <Text fz={28} fw={700} c={color}>{value}</Text>
    </Card>
  );
}

export default function RosterPage() {
  const { can } = useAuth();
  const onSite = useOnSite();
  const dashboard = useDashboard();
  const terminate = useTerminatePass();
  const [target, setTarget] = useState<OnSiteVisitor | null>(null);
  const [reason, setReason] = useState("");

  if (onSite.error) return <Container size="lg"><ErrorState error={onSite.error} /></Container>;

  const d = dashboard.data;
  const canTerminate = can("vms.pass.terminate");

  function submit() {
    if (!target) return;
    terminate.mutate({ pass_id: target.pass_id, reason: reason.trim() }, {
      onSuccess: () => {
        notifications.show({
          color: "green", message: `${target.visitor_name}'s pass was terminated. Security is alerted.` });
        setTarget(null);
        setReason("");
      },
    });
  }

  return (
    <Container size="lg">
      <PageHeader title="Roster" subtitle="Who is on campus right now. Refreshes every 30 seconds." />

      <SimpleGrid cols={{ base: 2, sm: 4 }} mb="lg">
        <Stat label="On site" value={d?.on_site ?? onSite.data?.results.length ?? 0} />
        <Stat label="Overstaying" value={d?.overstays.count ?? 0}
          color={d && d.overstays.count > 0 ? "red" : undefined} />
        <Stat label="Open alerts" value={d?.open_alerts.total ?? 0}
          color={d && d.open_alerts.total > 0 ? "orange" : undefined} />
        <Stat label="Zones in use" value={d?.by_zone.length ?? 0} />
      </SimpleGrid>

      <DataTable<OnSiteVisitor>
        rows={onSite.data?.results ?? []}
        loading={onSite.isPending}
        rowKey={(v) => v.pass_id}
        empty={{ icon: FaListAlt, title: "Nobody is on site" }}
        columns={[
          { key: "visitor", header: "Visitor", render: (v) => (
            <Stack gap={0}>
              <Group gap={6}>
                <Text size="sm" fw={600}>{v.visitor_name}</Text>
                {v.overstay && <Badge size="xs" color="red" variant="light">overstay</Badge>}
                {v.terminated && <Badge size="xs" color="gray" variant="light">pending exit</Badge>}
              </Group>
              <Text size="xs" c="dimmed">{v.visitor_phone}</Text>
            </Stack>
          ) },
          { key: "host", header: "Host", render: (v) => (
            <Stack gap={0}>
              <Text size="sm">{v.host_name || `User ${v.host_user_id}`}</Text>
              <Text size="xs" c="dimmed">{v.host_department}</Text>
            </Stack>
          ) },
          { key: "zone", header: "Last seen", render: (v) => (
            `${v.zone_name || "—"} · ${formatDateTime(v.last_seen_at)}`
          ) },
          { key: "until", header: "Pass ends", render: (v) => formatDateTime(v.valid_until) },
          { key: "act", header: "", align: "right", render: (v) => (
            canTerminate && !v.terminated ? (
              <Button size="compact-xs" color="red" variant="light"
                onClick={() => { setReason(""); setTarget(v); }}>
                Terminate
              </Button>
            ) : null
          ) },
        ]}
      />

      <FormModal
        opened={target !== null} onClose={() => setTarget(null)}
        title="Terminate this visit" subtitle={target?.visitor_name}
        submitLabel="Terminate" danger onSubmit={submit} submitting={terminate.isPending}
        error={terminate.error} disabled={reason.trim().length === 0}
        disabledReason="A reason is required." size="md"
      >
        <Textarea
          label="Reason" description="Recorded with the termination." required autosize
          minRows={3} maxLength={255} value={reason}
          onChange={(e) => setReason(e.currentTarget.value)}
        />
      </FormModal>
    </Container>
  );
}
