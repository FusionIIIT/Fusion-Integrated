import { useState } from "react";
import { Badge, Button, Container, Group, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarCheck, FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApproveEvent, useCancelEvent, useEvents } from "../api/hooks";
import type { VmsEvent } from "../api/types";
import { formatWindow, humanise } from "../format";

const STATUS_COLOR: Record<string, string> = {
  draft: "gray", approved: "green", cancelled: "red", pending: "orange", completed: "blue",
};

export default function EventsPage() {
  const { data, isPending, error } = useEvents();
  const approve = useApproveEvent();
  const cancel = useCancelEvent();
  const [cancelling, setCancelling] = useState<VmsEvent | null>(null);
  const [reason, setReason] = useState("");

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  function doApprove(e: VmsEvent) {
    approve.mutate(e.id, {
      onSuccess: () => notifications.show({
        color: "green", message: `Passes for “${e.name}” are being issued.` }),
      onError: (err) => notifications.show({ color: "red", message: errorMessage(err) }),
    });
  }

  function doCancel() {
    if (!cancelling) return;
    cancel.mutate({ id: cancelling.id, reason: reason.trim() }, {
      onSuccess: () => {
        notifications.show({ color: "green", message: `“${cancelling.name}” was cancelled.` });
        setCancelling(null);
        setReason("");
      },
    });
  }

  return (
    <Container size="lg">
      <PageHeader title="Events" subtitle="Seminars, drives and other events with many visitors" />

      <DataTable<VmsEvent>
        rows={data ?? []}
        loading={isPending}
        rowKey={(e) => e.id}
        empty={{ icon: FaCalendarCheck, title: "No events yet" }}
        columns={[
          { key: "name", header: "Event", render: (e) => (
            <Stack gap={0}>
              <Text size="sm" fw={600}>{e.name}</Text>
              <Text size="xs" c="dimmed">{e.organizer || "No organiser listed"}</Text>
            </Stack>
          ) },
          { key: "when", header: "When", render: (e) => formatWindow(e.valid_from, e.valid_until) },
          { key: "lane", header: "Entry", render: (e) => (
            e.fast_lane ? <Badge size="xs" variant="light">fast lane</Badge> : "Standard"
          ) },
          { key: "status", header: "Status", render: (e) => (
            <Badge color={STATUS_COLOR[e.status] ?? "gray"} variant="light">{humanise(e.status)}</Badge>
          ) },
          { key: "act", header: "", align: "right", render: (e) => (
            e.status === "cancelled" ? null : (
              <Group gap={6} justify="flex-end" wrap="nowrap">
                <Button size="compact-xs" leftSection={<FaCheck size={10} />}
                  loading={approve.isPending && approve.variables === e.id}
                  onClick={() => doApprove(e)}>
                  Approve attendees
                </Button>
                <Button size="compact-xs" color="red" variant="light"
                  leftSection={<FaTimes size={10} />}
                  onClick={() => { setReason(""); setCancelling(e); }}>
                  Cancel
                </Button>
              </Group>
            )
          ) },
        ]}
      />

      <FormModal
        opened={cancelling !== null} onClose={() => setCancelling(null)}
        title="Cancel this event" subtitle={cancelling?.name}
        submitLabel="Cancel event" danger onSubmit={doCancel} submitting={cancel.isPending}
        error={cancel.error} disabled={reason.trim().length === 0}
        disabledReason="A reason is required." size="md"
      >
        <Textarea label="Reason" description="Attendees are told the event is cancelled."
          required autosize minRows={3} maxLength={255} value={reason}
          onChange={(e) => setReason(e.currentTarget.value)} />
      </FormModal>
    </Container>
  );
}
