import { useState } from "react";
import {
  Alert, Button, Card, Container, Group, Menu, Select, Stack, Text, Textarea,
} from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { NumberInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaChevronDown, FaInfoCircle, FaUsers } from "react-icons/fa";

import { errorMessage } from "../../lib/http";
import { DataTable } from "../../ui/components/DataTable";
import { ErrorState } from "../../ui/components/ErrorState";
import { FormModal } from "../../ui/components/FormModal";
import { PageHeader } from "../../ui/components/PageHeader";
import { StatusBadge } from "../../ui/components/StatusBadge";
import { CpiBadge } from "../../modules/placement/components/CpiBadge";
import {
  useApplicantTransition, useIssueMyOffer, useMyApplicants, useMyPostings,
  type Applicant,
} from "../api";

/** Only the moves a recruiter is allowed to drive. The server's state machine
 *  is the authority; this map is what turns its vocabulary into buttons. */
const LABELS: Record<string, string> = {
  under_review: "Move to review",
  shortlisted: "Shortlist",
  selected: "Mark selected",
  rejected: "Reject",
  offer_issued: "Issue offer",
};

/** The recruiter payload is narrower than the staff one and carries no
 *  `allowed_transitions`, so the next legal moves are derived from the status.
 *  An illegal choice is still refused server-side — this only decides which
 *  buttons are worth offering. */
function movesFor(status: string): string[] {
  switch (status) {
    case "submitted": return ["under_review", "rejected"];
    case "under_review": return ["shortlisted", "rejected"];
    case "shortlisted": return ["offer_issued", "rejected"];
    case "interview_scheduled": return ["selected", "rejected"];
    case "selected": return ["offer_issued"];
    default: return [];
  }
}

export default function RecruiterApplicantsPage() {
  const postings = useMyPostings();
  const [postingId, setPostingId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const { data, isPending, error } = useMyApplicants({
    posting: postingId ? Number(postingId) : undefined,
    status: status ?? undefined,
  });
  const transition = useApplicantTransition();

  const [rejecting, setRejecting] = useState<Applicant | null>(null);
  const [reason, setReason] = useState("");
  const [offering, setOffering] = useState<Applicant | null>(null);

  function run(a: Applicant, to: string, why = "") {
    transition.mutate({ id: a.id, to_status: to, reason: why }, {
      onSuccess: () => {
        notifications.show({
          color: "green", title: "Updated",
          message: `${a.candidate?.name ?? "Candidate"} moved to ${to.replace(/_/g, " ")}.`,
        });
        setRejecting(null);
      },
      onError: (e) => notifications.show({
        color: "red", title: "Could not update", message: errorMessage(e),
      }),
    });
  }

  function act(a: Applicant, to: string) {
    if (to === "offer_issued") { setOffering(a); return; }
    if (to === "rejected") { setRejecting(a); setReason(""); return; }
    run(a, to);
  }

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Applicants"
        subtitle="Candidates who applied to your roles"
        action={
          <Group gap="sm">
            <Select
              placeholder="All roles" clearable w={220} value={postingId}
              onChange={setPostingId}
              data={(postings.data?.results ?? []).map((p) => ({
                value: String(p.id), label: p.title,
              }))}
            />
            <Select
              placeholder="All statuses" clearable w={180} value={status}
              onChange={setStatus}
              data={["submitted", "under_review", "shortlisted",
                "interview_scheduled", "selected", "offer_issued",
                "offer_accepted", "rejected"].map((v) => ({
                  value: v, label: v.replace(/_/g, " "),
                }))}
            />
          </Group>
        }
      />

      <Card padding="lg">
        <DataTable<Applicant>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={960}
          columns={[
            {
              key: "candidate", header: "Candidate",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600}>{r.candidate?.name}</Text>
                  <Text size="xs" c="dimmed">
                    {r.candidate?.roll_no}
                    {r.candidate?.discipline ? ` · ${r.candidate.discipline}` : ""}
                    {r.candidate?.batch_year ? ` · ${r.candidate.batch_year}` : ""}
                  </Text>
                </Stack>
              ),
            },
            {
              key: "cpi", header: "CPI",
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
            {
              key: "cover_note", header: "Note",
              render: (r) => (
                <Text size="sm" lineClamp={2} maw={280}>
                  {r.cover_note || "—"}
                </Text>
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
                const moves = movesFor(r.status);
                if (!moves.length) return <Text size="xs" c="dimmed">—</Text>;
                return (
                  <Menu position="bottom-end" withinPortal>
                    <Menu.Target>
                      <Button size="xs" variant="light"
                        rightSection={<FaChevronDown size={9} />}>
                        Action
                      </Button>
                    </Menu.Target>
                    <Menu.Dropdown>
                      {moves.map((t) => (
                        <Menu.Item
                          key={t} color={t === "rejected" ? "red" : undefined}
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
            title: "No applicants yet",
            description:
              "Candidates appear here once they apply to a published role.",
          }}
        />
      </Card>

      <FormModal
        opened={rejecting != null} onClose={() => setRejecting(null)}
        title="Reject this candidate"
        subtitle={rejecting?.candidate?.name}
        onSubmit={() => rejecting && run(rejecting, "rejected", reason)}
        submitLabel="Reject" danger submitting={transition.isPending}
        disabled={!reason.trim()}
      >
        <Stack gap="sm">
          <Textarea
            label="Reason" required autosize minRows={3} value={reason}
            onChange={(e) => setReason(e.currentTarget.value)} maxLength={300}
          />
          <Text size="xs" c="dimmed">
            Recorded permanently and visible to the placement office.
          </Text>
        </Stack>
      </FormModal>

      <IssueOfferModal
        applicant={offering} onClose={() => setOffering(null)}
      />
    </Container>
  );
}

function IssueOfferModal({ applicant, onClose }: {
  applicant: Applicant | null; onClose: () => void;
}) {
  const issue = useIssueMyOffer();
  const [ctc, setCtc] = useState<number | string>("");
  const [respondBy, setRespondBy] = useState<Date | null>(null);

  return (
    <FormModal
      opened={applicant != null} onClose={onClose}
      title="Issue an offer"
      subtitle={applicant?.candidate?.name}
      onSubmit={() => applicant && issue.mutate(
        {
          application_id: applicant.id,
          ctc_lpa: ctc === "" ? undefined : String(ctc),
          respond_by: respondBy ? respondBy.toISOString() : undefined,
        },
        {
          onSuccess: () => {
            notifications.show({
              color: "green", title: "Offer issued",
              message: "The candidate has been notified with the deadline.",
            });
            setCtc(""); setRespondBy(null);
            onClose();
          },
          onError: (e) => notifications.show({
            color: "red", title: "Could not issue offer",
            message: errorMessage(e),
          }),
        },
      )}
      submitLabel="Issue offer" submitting={issue.isPending} error={issue.error}
    >
      <Stack gap="md">
        <NumberInput
          label="CTC (LPA)" value={ctc} onChange={setCtc}
          decimalScale={2} min={0}
          description="Leave blank to use the posting's CTC"
        />
        <DateTimePicker
          label="Respond by" value={respondBy} onChange={setRespondBy}
          description="Leave blank to use the institute's default window"
        />
        <Alert variant="light" color="blue" icon={<FaInfoCircle />}>
          <Text size="sm">
            Whether the candidate may accept is decided by institute placement
            policy. If they already hold an offer, yours may be refused or may
            supersede it.
          </Text>
        </Alert>
      </Stack>
    </FormModal>
  );
}
