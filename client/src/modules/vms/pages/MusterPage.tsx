import { useState } from "react";
import {
  Alert, Badge, Button, Card, Container, Group, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaExclamationTriangle, FaRunning } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCloseMuster, useCurrentMuster, useMusterRoster, useRollCall, useTriggerMuster,
} from "../api/hooks";
import type { Muster, MusterEntry } from "../api/types";
import { formatDateTime, humanise } from "../format";

const STATUS_COLOR: Record<string, string> = {
  accounted: "green", evacuated: "teal", unaccounted: "red", pending: "orange",
};

function OpenMuster({ muster }: { muster: Muster }) {
  const { can } = useAuth();
  const roster = useMusterRoster(muster.id);
  const rollCall = useRollCall(muster.id);
  const close = useCloseMuster(muster.id);
  const [closing, setClosing] = useState(false);
  const [note, setNote] = useState("");
  const rows = roster.data?.results ?? [];
  const outstanding = rows.filter((r) => r.status !== "accounted" && r.status !== "evacuated").length;

  function mark(entry: MusterEntry, status: "accounted" | "evacuated") {
    rollCall.mutate({ pass_id: entry.pass_id, status }, {
      onError: (e) => notifications.show({ color: "red", message: errorMessage(e) }),
    });
  }

  function finish() {
    close.mutate({ note: note.trim(), force: outstanding > 0 }, {
      onSuccess: () => {
        notifications.show({ color: "green", message: "Muster closed. The report is ready." });
        setClosing(false);
        setNote("");
      },
    });
  }

  return (
    <>
      <Alert color="red" variant="light" icon={<FaExclamationTriangle />}
        title={`Emergency muster open since ${formatDateTime(muster.triggered_at)}`} mb="md">
        <Group justify="space-between">
          <Text size="sm">
            {rows.length - outstanding} of {rows.length} visitors accounted for.
            {muster.reason ? ` Reason: ${muster.reason}` : ""}
          </Text>
          {can("vms.muster.trigger") && (
            <Button size="compact-sm" color="red" onClick={() => setClosing(true)}>
              Close muster
            </Button>
          )}
        </Group>
      </Alert>

      <DataTable<MusterEntry>
        rows={rows}
        loading={roster.isPending}
        rowKey={(r) => r.pass_id}
        empty={{ title: "Nobody was on site when the muster started" }}
        columns={[
          { key: "name", header: "Visitor", render: (r) => r.visitor_name },
          { key: "zone", header: "Last zone", render: (r) => r.last_zone_name || "—" },
          { key: "host", header: "Host", render: (r) => r.host_name || "—" },
          { key: "status", header: "Status", render: (r) => (
            <Badge color={STATUS_COLOR[r.status] ?? "gray"} variant="light">{humanise(r.status)}</Badge>
          ) },
          { key: "act", header: "", align: "right", render: (r) => (
            <Group gap={6} justify="flex-end" wrap="nowrap">
              <Button size="compact-xs" variant="light" leftSection={<FaCheck size={10} />}
                loading={rollCall.isPending && rollCall.variables?.pass_id === r.pass_id}
                onClick={() => mark(r, "accounted")}>
                Accounted
              </Button>
              <Button size="compact-xs" variant="default" onClick={() => mark(r, "evacuated")}>
                Evacuated
              </Button>
            </Group>
          ) },
        ]}
      />

      <FormModal
        opened={closing} onClose={() => setClosing(false)} title="Close the muster"
        subtitle={outstanding > 0 ? `${outstanding} visitors are not yet accounted for` : undefined}
        submitLabel="Close muster" danger onSubmit={finish} submitting={close.isPending}
        error={close.error} size="md"
      >
        <Textarea label="Closing note" autosize minRows={3} maxLength={1000} value={note}
          onChange={(e) => setNote(e.currentTarget.value)} />
      </FormModal>
    </>
  );
}

export default function MusterPage() {
  const { can } = useAuth();
  const current = useCurrentMuster();
  const trigger = useTriggerMuster();
  const [starting, setStarting] = useState(false);
  const [reason, setReason] = useState("");

  if (current.error) return <Container size="lg"><ErrorState error={current.error} /></Container>;

  function start() {
    trigger.mutate(reason.trim(), {
      onSuccess: () => {
        notifications.show({ color: "red", message: "Muster started. Visitors are being alerted." });
        setStarting(false);
        setReason("");
      },
    });
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Muster"
        subtitle="Emergency roll call of everyone who is on campus"
        action={!current.data && can("vms.muster.trigger") && (
          <Button color="red" leftSection={<FaRunning size={12} />} onClick={() => setStarting(true)}>
            Start emergency muster
          </Button>
        )}
      />

      {current.isPending && <Text c="dimmed">Loading…</Text>}
      {current.data && <OpenMuster muster={current.data} />}
      {!current.isPending && !current.data && (
        <Card withBorder padding="xl">
          <Stack align="center" gap={4}>
            <Text fw={600}>No muster in progress</Text>
            <Text size="sm" c="dimmed">Start one only in a real emergency or a drill.</Text>
          </Stack>
        </Card>
      )}

      <FormModal
        opened={starting} onClose={() => setStarting(false)} title="Start an emergency muster"
        subtitle="Every visitor on site is alerted and listed for roll call"
        submitLabel="Start muster" danger onSubmit={start} submitting={trigger.isPending}
        error={trigger.error} size="md"
      >
        <Textarea label="Reason (optional)" autosize minRows={2} maxLength={500} value={reason}
          onChange={(e) => setReason(e.currentTarget.value)} />
      </FormModal>
    </Container>
  );
}
