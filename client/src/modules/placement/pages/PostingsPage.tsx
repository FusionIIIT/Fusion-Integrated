import { useState } from "react";
import {
  Badge, Button, Card, Container, Drawer, Group, Stack, Text, Textarea, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaClipboardList, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { EligibilityPanel } from "../components/EligibilityPanel";
import { NewPostingModal } from "../components/NewPostingModal";
import {
  useApply, useEligibility, usePostings, usePublishPosting,
} from "../api/hooks";
import type { Posting } from "../api/types";

function deadline(p: Posting): string {
  if (!p.closes_at) return "—";
  const d = new Date(p.closes_at);
  const days = Math.ceil((d.getTime() - Date.now()) / 86_400_000);
  if (days < 0) return "closed";
  return `${d.toLocaleDateString()} (${days}d)`;
}

export default function PostingsPage() {
  const { data, isPending, error } = usePostings();
  const { can } = useAuth();
  const [selected, setSelected] = useState<Posting | null>(null);
  const [creating, setCreating] = useState(false);

  const canManage = can("placement_cell.job_posting.manage");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  return (
    <Container size="xl">
      <PageHeader
        title="Opportunities"
        subtitle={canManage
          ? "Every posting for the active placement year"
          : "Openings you can apply to"}
        action={canManage && (
          <Button leftSection={<FaPlus size={12} />} onClick={() => setCreating(true)}>
            New posting
          </Button>
        )}
      />

      <Card padding="lg">
        <DataTable<Posting>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "title", header: "Role",
              render: (r) => (
                <Stack gap={0}>
                  <Text
                    fw={600} style={{ cursor: "pointer" }}
                    onClick={() => setSelected(r)}
                  >
                    {r.title}
                  </Text>
                  <Text size="xs" c="dimmed">{r.location || "—"}</Text>
                </Stack>
              ),
            },
            { key: "company", header: "Company",
              render: (r) => r.company?.name ?? "—" },
            {
              key: "kind", header: "Type",
              render: (r) => (
                <Badge variant="default" size="sm">
                  {r.kind === "fte" ? "Full time"
                    : r.kind === "ppo" ? "PPO" : "Internship"}
                </Badge>
              ),
            },
            { key: "ctc_lpa", header: "CTC (LPA)", align: "right",
              render: (r) => r.ctc_lpa ?? "—" },
            { key: "seats", header: "Seats", align: "right",
              render: (r) => r.seats?.toString() ?? "—" },
            { key: "closes_at", header: "Applications close",
              render: (r) => deadline(r) },
            { key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} /> },
          ]}
          empty={{
            icon: FaClipboardList,
            title: "No postings yet",
            description: canManage
              ? "Create a posting, then publish it to make it visible."
              : "Published openings will appear here.",
          }}
        />
      </Card>

      <PostingDrawer
        posting={selected} onClose={() => setSelected(null)} canManage={canManage}
      />
      <NewPostingModal opened={creating} onClose={() => setCreating(false)} />
    </Container>
  );
}

function PostingDrawer({ posting, onClose, canManage }: {
  posting: Posting | null;
  onClose: () => void;
  canManage: boolean;
}) {
  const { can } = useAuth();
  const [note, setNote] = useState("");
  const eligibility = useEligibility(posting?.id);
  const apply = useApply();
  const publish = usePublishPosting();

  const canApply = can("placement_cell.application.create");
  // The server decides and re-checks on submit; the button only follows.
  const isEligible = eligibility.data?.is_eligible === true;

  function submit() {
    if (!posting) return;
    apply.mutate(
      { posting_id: posting.id, cover_note: note },
      {
        onSuccess: () => {
          notifications.show({
            color: "green", title: "Application submitted",
            message: `Your application to ${posting.title} has been recorded.`,
          });
          setNote("");
          onClose();
        },
        onError: (e) => notifications.show({
          color: "red", title: "Could not apply", message: errorMessage(e),
        }),
      },
    );
  }

  return (
    <Drawer
      opened={posting != null} onClose={onClose} position="right" size="lg"
      title={<Text fw={700}>{posting?.title}</Text>}
    >
      {posting && (
        <Stack gap="md">
          <Group gap="xs">
            <StatusBadge status={posting.status} />
            <Text size="sm" c="dimmed">
              {posting.company.name}
              {posting.location ? ` · ${posting.location}` : ""}
            </Text>
          </Group>

          <Group gap="xl">
            <Stat label="CTC (LPA)" value={posting.ctc_lpa ?? "—"} />
            <Stat label="Stipend / month" value={posting.stipend_pm ?? "—"} />
            <Stat label="Seats" value={posting.seats?.toString() ?? "—"} />
            <Stat
              label="Closes"
              value={posting.closes_at
                ? new Date(posting.closes_at).toLocaleString() : "—"}
            />
          </Group>

          <div>
            <Title order={5} mb={4}>Role</Title>
            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
              {posting.description || "No description recorded."}
            </Text>
          </div>

          {canApply && (
            <>
              <EligibilityPanel
                verdict={eligibility.data}
                isPending={eligibility.isPending}
                error={eligibility.error}
              />
              <Textarea
                label="Cover note (optional)"
                placeholder="Anything the recruiter should know"
                value={note} onChange={(e) => setNote(e.currentTarget.value)}
                autosize minRows={3} maxLength={4000}
                disabled={!isEligible}
              />
              <Button
                onClick={submit} loading={apply.isPending} disabled={!isEligible}
              >
                {isEligible ? "Apply" : "Not eligible"}
              </Button>
            </>
          )}

          {canManage && posting.status === "draft" && (
            <Button
              variant="light"
              loading={publish.isPending}
              onClick={() => publish.mutate(posting.id, {
                onSuccess: () => {
                  notifications.show({
                    color: "green", title: "Published",
                    message: "Eligibility criteria are now frozen.",
                  });
                  onClose();
                },
                onError: (e) => notifications.show({
                  color: "red", title: "Could not publish",
                  message: errorMessage(e),
                }),
              })}
            >
              Publish this posting
            </Button>
          )}
        </Stack>
      )}
    </Drawer>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Stack gap={0}>
      <Text size="xs" c="dimmed" tt="uppercase">{label}</Text>
      <Text fw={600}>{value}</Text>
    </Stack>
  );
}
