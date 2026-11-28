import { useState } from "react";
import {
  Anchor, Button, Checkbox, Drawer, Group, Loader, Progress, Stack, Text, Textarea,
} from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useApproveMemberships, useBudgetRequests, useManagedPolls, useMemberships, useReports,
} from "../api/hooks";
import type { Club } from "../api/types";
import { notifyDone, notifyFailed } from "./notify";

interface DrawerProps { club: Club; onClose: () => void }

function Body({ isPending, error, empty, children }: {
  isPending: boolean; error: unknown; empty: boolean; children: React.ReactNode;
}) {
  if (error) return <ErrorState error={error} />;
  if (isPending) return <Loader size="sm" />;
  if (empty) return <Text c="dimmed" size="sm">Nothing here yet.</Text>;
  return <>{children}</>;
}

/** UC-GYM-005: select pending applications and approve them together. */
export function MembershipRequests({ club, onClose }: DrawerProps) {
  const { data, isPending, error } = useMemberships({ club: club.id, status: "open" });
  const approve = useApproveMemberships();
  const [picked, setPicked] = useState<number[]>([]);
  const [remarks, setRemarks] = useState("");
  const rows = data?.results ?? [];

  function submit() {
    approve.mutate({ ids: picked, remarks }, {
      onSuccess: (out) => {
        const done = out.filter((o) => o.outcome === "approved").length;
        const refused = out.filter((o) => o.outcome !== "approved");
        notifyDone("Applications decided", `${done} approved.`
          + (refused.length ? ` Not changed: ${refused.map((o) => o.message).join(" ")}` : ""));
        setPicked([]);
      },
      onError: (e) => notifyFailed("Could not approve", e),
    });
  }

  return (
    <Drawer opened onClose={onClose} position="right" size="md"
      title={`Pending applications · ${club.name}`}>
      <Body isPending={isPending} error={error} empty={rows.length === 0}>
        <Stack>
          {rows.map((m) => (
            <Checkbox key={m.id} checked={picked.includes(m.id)}
              label={`${m.applicant_name || `User ${m.user_id}`}: ${m.description}`}
              onChange={(e) => setPicked((p) => e.currentTarget.checked
                ? [...p, m.id] : p.filter((x) => x !== m.id))} />))}
          <Textarea label="Remarks (optional)" maxLength={1000} value={remarks}
            onChange={(e) => setRemarks(e.currentTarget.value)} />
          <Group><Button onClick={submit} disabled={!picked.length} loading={approve.isPending}>
            Approve selected</Button></Group>
        </Stack>
      </Body>
    </Drawer>
  );
}

/** AFR-GYM-028: counts only, to the club's own leaders. */
export function PollResults({ club, onClose }: DrawerProps) {
  const { data, isPending, error } = useManagedPolls(club.id);
  const rows = data?.results ?? [];
  return (
    <Drawer opened onClose={onClose} position="right" size="md" title={`Polls · ${club.name}`}>
      <Body isPending={isPending} error={error} empty={rows.length === 0}>
        <Stack>
          {rows.map((p) => (
            <Stack key={p.id} gap={4}>
              <Text fw={600}>{p.title}</Text>
              <Text size="xs" c="dimmed">Open until {p.expires_on} · {p.total_votes} vote(s)</Text>
              {p.choices.map((c) => (
                <div key={c.id}>
                  <Text size="sm">{c.label}: {c.votes ?? 0}</Text>
                  <Progress aria-label={`${c.label} share`}
                    value={p.total_votes ? ((c.votes ?? 0) * 100) / p.total_votes : 0} />
                </div>))}
            </Stack>))}
        </Stack>
      </Body>
    </Drawer>
  );
}

/** AFR-GYM-031: tracking only. */
export function BudgetList({ club, onClose }: DrawerProps) {
  const { data, isPending, error } = useBudgetRequests(club.id);
  const rows = data?.results ?? [];
  return (
    <Drawer opened onClose={onClose} position="right" size="md"
      title={`Budget requests · ${club.name}`}>
      <Body isPending={isPending} error={error} empty={rows.length === 0}>
        <Stack>{rows.map((b) => (
          <div key={b.id}>
            <Text fw={600}>{b.purpose} · ₹{b.amount}</Text>
            <Text size="xs" c="dimmed">{b.status} · {new Date(b.created_at).toLocaleDateString()}</Text>
            <Anchor size="sm" href={b.document_link} target="_blank" rel="noreferrer noopener">
              Supporting document</Anchor>
          </div>))}</Stack>
      </Body>
    </Drawer>
  );
}

export function ReportList({ club, onClose }: DrawerProps) {
  const { data, isPending, error } = useReports(club.id);
  const rows = data?.results ?? [];
  return (
    <Drawer opened onClose={onClose} position="right" size="md"
      title={`Event reports · ${club.name}`}>
      <Body isPending={isPending} error={error} empty={rows.length === 0}>
        <Stack>{rows.map((r) => (
          <div key={r.id}>
            <Text fw={600}>{r.event_name}</Text>
            <Text size="xs" c="dimmed">{new Date(r.event_at).toLocaleString()}</Text>
            <Anchor size="sm" href={r.report_link} target="_blank" rel="noreferrer noopener">
              Report file</Anchor>
          </div>))}</Stack>
      </Body>
    </Drawer>
  );
}
