import { useState } from "react";
import { Badge, Button, Container, Group, Stack, Text, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaStamp, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable, type RowKey } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBulkDecide, useDecide, useHostRequests } from "../api/hooks";
import type { HostRequest } from "../api/types";
import { formatDateTime, formatWindow } from "../format";

export default function ApprovalsPage() {
  const { data, isPending, error } = useHostRequests("pending");
  const decide = useDecide();
  const bulk = useBulkDecide();
  const [selected, setSelected] = useState<Set<RowKey>>(new Set());
  const [rejecting, setRejecting] = useState<HostRequest | null>(null);
  const [note, setNote] = useState("");

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  const rows = data?.results ?? [];

  function fail(e: unknown) {
    notifications.show({ color: "red", message: errorMessage(e) });
  }

  function approve(r: HostRequest) {
    decide.mutate({ id: r.id, decision: "approve" }, {
      onSuccess: () => notifications.show({
        color: "green", message: `Approved ${r.visitor_name}. A pass was issued.` }),
      onError: fail,
    });
  }

  function reject() {
    if (!rejecting) return;
    decide.mutate({ id: rejecting.id, decision: "reject", note: note.trim() }, {
      onSuccess: () => {
        notifications.show({ color: "green", message: `Rejected ${rejecting.visitor_name}.` });
        setRejecting(null);
        setNote("");
      },
    });
  }

  function approveSelected() {
    bulk.mutate({ ids: [...selected].map(Number), decision: "approve" }, {
      onSuccess: ({ results }) => {
        const failed = results.filter((r) => !r.ok).length;
        setSelected(new Set());
        notifications.show({
          color: failed ? "orange" : "green",
          message: failed
            ? `Approved ${results.length - failed}; ${failed} could not be approved.`
            : `Approved ${results.length} request${results.length === 1 ? "" : "s"}.`,
        });
      },
      onError: fail,
    });
  }

  return (
    <Container size="lg">
      <PageHeader
        title="Approvals"
        subtitle="Visit requests waiting for your decision"
        action={selected.size > 0 && (
          <Button
            leftSection={<FaCheck size={12} />} loading={bulk.isPending} onClick={approveSelected}
          >
            Approve {selected.size} selected
          </Button>
        )}
      />

      <DataTable<HostRequest>
        rows={rows}
        loading={isPending}
        rowKey={(r) => r.id}
        selection={{ selected, onChange: setSelected }}
        empty={{ icon: FaStamp, title: "Nothing waiting for you",
          description: "New visit requests will appear here." }}
        columns={[
          { key: "visitor", header: "Visitor", render: (r) => (
            <Stack gap={0}>
              <Group gap={6}>
                <Text size="sm" fw={600}>{r.visitor_name}</Text>
                {r.is_urgent && <Badge size="xs" color="orange" variant="light">urgent</Badge>}
              </Group>
              <Text size="xs" c="dimmed">{r.purpose}</Text>
            </Stack>
          ) },
          { key: "window", header: "Visit", render: (r) => formatWindow(r.scheduled_start, r.scheduled_end) },
          { key: "expires", header: "Decide by", render: (r) => formatDateTime(r.expires_at) },
          { key: "actions", header: "", align: "right", render: (r) => (
            <Group gap={6} justify="flex-end" wrap="nowrap">
              <Button
                size="compact-sm" leftSection={<FaCheck size={10} />}
                loading={decide.isPending && decide.variables?.id === r.id}
                onClick={() => approve(r)}
              >
                Approve
              </Button>
              <Button
                size="compact-sm" color="red" variant="light" leftSection={<FaTimes size={10} />}
                onClick={() => { setNote(""); setRejecting(r); }}
              >
                Reject
              </Button>
            </Group>
          ) },
        ]}
      />
      {data?.next && (
        <Text size="xs" c="dimmed" mt="sm">
          More requests are waiting. Decide these first and the next ones will load.
        </Text>
      )}

      <FormModal
        opened={rejecting !== null} onClose={() => setRejecting(null)}
        title="Reject visit request" subtitle={rejecting?.visitor_name}
        submitLabel="Reject" danger onSubmit={reject}
        submitting={decide.isPending} error={decide.error}
        disabled={note.trim().length === 0} disabledReason="A reason is required to reject."
        size="md"
      >
        <Textarea
          label="Reason" description="The visitor is told why." required autosize minRows={3}
          maxLength={255} value={note} onChange={(e) => setNote(e.currentTarget.value)}
        />
      </FormModal>
    </Container>
  );
}
