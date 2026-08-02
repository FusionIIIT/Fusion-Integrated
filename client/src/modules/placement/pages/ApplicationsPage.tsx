import { useState } from "react";
import {
  Button, Card, Container, Menu, Select, Stack, Text, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaChevronDown, FaUsers } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { CpiBadge } from "../components/CpiBadge";
import { IssueOfferModal } from "../components/IssueOfferModal";
import { useApplications, useTransition } from "../api/hooks";
import type { Application } from "../api/types";

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

      <Card padding="lg">
        <DataTable<Application>
          rows={(data?.results ?? []) as Application[]}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={1000}
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
                if (!moves.length) return <Text size="xs" c="dimmed">—</Text>;
                return (
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
    </Container>
  );
}
