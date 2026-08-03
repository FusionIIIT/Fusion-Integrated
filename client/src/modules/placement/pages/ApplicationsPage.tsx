import { useMemo, useState } from "react";
import {
  ActionIcon, Alert, Badge, Button, Card, Container, Group, Menu, Paper, Select,
  Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaChevronDown, FaExclamationTriangle, FaHistory, FaUsers,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { CpiBadge } from "../components/CpiBadge";
import { HistoryDrawer } from "../components/HistoryDrawer";
import { IssueOfferModal } from "../components/IssueOfferModal";
import { useApplications, useBulkTransition, useTransition } from "../api/hooks";
import type { BulkResult } from "../api/hooks";
import type { Application } from "../api/types";
import type { RowKey } from "../../../ui/components/DataTable";

/** Bulk targets a TPO actually reaches for. Anything else stays a per-row
 *  decision, because it needs looking at the individual candidate. */
const BULK_MOVES = [
  { value: "under_review", label: "Move to review" },
  { value: "shortlisted", label: "Shortlist" },
  { value: "rejected", label: "Reject" },
];

/** Transitions that must carry a reason. The server enforces this too — the
 *  prompt here just avoids a round trip that would only produce an error. */
const NEEDS_REASON = new Set(["rejected"]);

const LABELS: Record<string, string> = {
  under_review: "Move to review",
  shortlisted: "Shortlist",
  interview_scheduled: "Mark interview scheduled",
  selected: "Mark selected",
  rejected: "Reject",
  offer_issued: "Issue offer",
};

export default function ApplicationsPage() {
  const [status, setStatus] = useState<string | null>(null);
  const { data, isPending, error } = useApplications(
    status ? { status } : undefined);
  const [pending, setPending] = useState<
    { app: Application; to: string } | null>(null);
  const [offerFor, setOfferFor] = useState<Application | null>(null);
  const [reason, setReason] = useState("");
  const transition = useTransition();

  const [selected, setSelected] = useState<Set<RowKey>>(new Set());
  const [bulkTo, setBulkTo] = useState<string | null>(null);
  const [bulkReason, setBulkReason] = useState("");
  const [lastBulk, setLastBulk] = useState<BulkResult | null>(null);
  const [historyFor, setHistoryFor] = useState<number | null>(null);
  const bulk = useBulkTransition();

  const rows = useMemo(
    () => (data?.results ?? []) as Application[], [data]);

  // A terminal application cannot move, so offering its checkbox would only
  // produce refusals the user has to read past.
  const isSelectable = (row: Application) =>
    (row.allowed_transitions ?? []).some(
      (t) => BULK_MOVES.some((m) => m.value === t));

  function runBulk() {
    if (!bulkTo || !selected.size) return;
    bulk.mutate(
      {
        application_ids: [...selected].map(Number),
        to_status: bulkTo,
        reason: bulkReason,
      },
      {
        onSuccess: (result) => {
          setLastBulk(result);
          notifications.show({
            color: result.refused ? "orange" : "green",
            title: result.refused
              ? `${result.moved} moved, ${result.refused} refused`
              : `${result.moved} moved`,
            message: result.refused
              ? "Some could not be moved — see the note above the table."
              : "Every selected application was updated.",
          });
          // Only clear what actually moved, so a retry keeps the rest selected.
          const movedIds = new Set(result.results
            .filter((r) => r.moved).map((r) => r.application_id));
          setSelected(new Set([...selected].filter(
            (id) => !movedIds.has(Number(id)))));
          setBulkTo(null);
          setBulkReason("");
        },
        onError: (e) => notifications.show({
          color: "red", title: "Bulk action failed", message: errorMessage(e),
        }),
      },
    );
  }

  function run(app: Application, to: string, why: string) {
    transition.mutate(
      { id: app.id, to_status: to, reason: why },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Updated",
            message: `Application moved to ${to.replace(/_/g, " ")}.`,
          });
          setPending(null);
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not update", message: errorMessage(e),
        }),
      },
    );
  }

  function act(app: Application, to: string) {
    if (to === "offer_issued") { setOfferFor(app); return; }
    if (NEEDS_REASON.has(to)) { setPending({ app, to }); setReason(""); return; }
    run(app, to, "");
  }

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Applications"
        subtitle="Review, shortlist and progress candidates"
        action={
          <Select
            placeholder="All statuses" clearable value={status}
            onChange={setStatus} w={200}
            data={["submitted", "under_review", "shortlisted",
              "interview_scheduled", "selected", "offer_issued",
              "offer_accepted", "rejected"].map((v) => ({
                value: v, label: v.replace(/_/g, " "),
              }))}
          />
        }
      />

      {/* Appears only with a selection, so it never competes with the table for
          attention when there is nothing to act on. */}
      {selected.size > 0 && (
        <Paper
          withBorder p="sm" mb="md" radius="md"
          bg="var(--mantine-color-blue-0)"
        >
          <Group justify="space-between" wrap="nowrap">
            <Group gap="sm" wrap="nowrap">
              <Badge variant="filled">{selected.size} selected</Badge>
              <Button
                variant="subtle" size="xs"
                onClick={() => setSelected(new Set())}
              >
                Clear
              </Button>
            </Group>
            <Group gap="xs" wrap="nowrap">
              <Select
                data={BULK_MOVES} value={bulkTo} onChange={setBulkTo}
                placeholder="Choose an action" w={190} size="xs"
              />
              <Button
                size="xs" loading={bulk.isPending}
                color={bulkTo === "rejected" ? "red" : undefined}
                disabled={!bulkTo
                  || (bulkTo === "rejected" && !bulkReason.trim())}
                onClick={runBulk}
              >
                Apply
              </Button>
            </Group>
          </Group>

          {/* Rejection needs a reason per item; the server refuses without one,
              so asking here avoids a round trip that only returns errors. */}
          {bulkTo === "rejected" && (
            <Textarea
              mt="sm" label="Reason" required autosize minRows={2}
              value={bulkReason}
              onChange={(e) => setBulkReason(e.currentTarget.value)}
              description="Recorded against every selected application, and sent to each student."
              maxLength={300}
            />
          )}
        </Paper>
      )}

      {lastBulk && lastBulk.refused > 0 && (
        <Alert
          variant="light" color="orange" icon={<FaExclamationTriangle />}
          mb="md" withCloseButton onClose={() => setLastBulk(null)}
          title={`${lastBulk.moved} moved, ${lastBulk.refused} could not be`}
        >
          <Stack gap={2}>
            {lastBulk.results.filter((r) => !r.moved).slice(0, 8).map((r) => (
              <Text size="sm" key={r.application_id}>
                #{r.application_id} — {r.error}
              </Text>
            ))}
          </Stack>
        </Alert>
      )}

      <Card padding="lg">
        <DataTable<Application>
          rows={rows}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={1000}
          selection={{ selected, onChange: setSelected, isSelectable }}
          columns={[
            {
              key: "candidate", header: "Candidate",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.candidate?.name || `User ${r.user_id}`}</Text>
                  <Text size="xs" c="dimmed">
                    {r.candidate?.roll_no}
                    {r.candidate?.discipline ? ` · ${r.candidate.discipline}` : ""}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "posting", header: "Applied for",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm">{r.posting?.title}</Text>
                  <Text size="xs" c="dimmed">{r.posting?.company?.name}</Text>
                </Stack>
              ),
            },
            {
              key: "cpi", header: "CPI at apply",
              render: (r) => (
                <CpiBadge
                  cpi={r.cpi_at_apply}
                  standing={{
                    semester: r.semester_at_apply, semester_type: null,
                    declared_seq: null, synced_at: null, computed_by: null,
                  }}
                />
              ),
            },
            { key: "applied_at", header: "Applied",
              render: (r) => r.applied_at
                ? new Date(r.applied_at).toLocaleDateString() : "—" },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
            {
              key: "actions", header: "", align: "right",
              render: (r) => {
                // The server says what is legal; there is no client-side
                // state machine to drift out of sync with it.
                const moves = (r.allowed_transitions ?? [])
                  .filter((t) => LABELS[t]);
                return (
                  <Group gap={4} justify="flex-end" wrap="nowrap">
                    <ActionIcon
                      variant="subtle" color="gray" aria-label="History"
                      onClick={() => setHistoryFor(r.id)}
                    >
                      <FaHistory size={12} />
                    </ActionIcon>
                    {moves.length > 0 && (
                      <Menu position="bottom-end" withinPortal>
                        <Menu.Target>
                          <Button
                            size="xs" variant="light"
                            rightSection={<FaChevronDown size={9} />}
                          >
                            Action
                          </Button>
                        </Menu.Target>
                        <Menu.Dropdown>
                          {moves.map((t) => (
                            <Menu.Item
                              key={t}
                              color={t === "rejected" ? "red" : undefined}
                              onClick={() => act(r, t)}
                            >
                              {LABELS[t]}
                            </Menu.Item>
                          ))}
                        </Menu.Dropdown>
                      </Menu>
                    )}
                  </Group>
                );
              },
            },
          ]}
          empty={{
            icon: FaUsers,
            title: "No applications",
            description: "Applications appear here once students apply.",
          }}
        />
      </Card>

      <FormModal
        opened={pending != null} onClose={() => setPending(null)}
        title={`${LABELS[pending?.to ?? ""] ?? "Update"} application`}
        subtitle="Recorded permanently in the audit trail, and the student is notified"
        onSubmit={() => pending && run(pending.app, pending.to, reason)}
        submitLabel="Confirm" danger submitting={transition.isPending}
        disabled={!reason.trim()}
      >
        <Textarea
          label="Reason" required autosize minRows={3} value={reason}
          onChange={(e) => setReason(e.currentTarget.value)}
          description="Required for a rejection."
          maxLength={300}
        />
      </FormModal>

      <IssueOfferModal application={offerFor} onClose={() => setOfferFor(null)} />

      <HistoryDrawer
        applicationId={historyFor} onClose={() => setHistoryFor(null)}
      />
    </Container>
  );
}
