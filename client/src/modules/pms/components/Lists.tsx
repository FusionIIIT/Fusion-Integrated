import { Button, Group, TextInput } from "@mantine/core";
import { useState } from "react";
import { FaInbox } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useApplications, useMyWork } from "../api/hooks";
import type { ApplicationRow, WorkItem } from "../api/types";
import { ApplicationDrawer } from "./ApplicationDrawer";
import { day, words } from "./format";

// The caller's pending items of the given kinds, each opening its application.
export function WorkQueue({ kinds, emptyTitle }: { kinds: string[]; emptyTitle: string }) {
  const work = useMyWork();
  const [open, setOpen] = useState<number | null>(null);
  if (work.error) return <ErrorState error={work.error} />;
  const rows = (work.data ?? []).filter((w) => kinds.includes(w.kind));
  return (
    <>
      <DataTable<WorkItem>
        rows={rows} loading={work.isPending} rowKey={(r) => `${r.kind}-${r.id}`}
        empty={{ icon: FaInbox, title: emptyTitle }}
        columns={[
          { key: "kind", header: "Waiting on you", render: (r) => words(r.kind) },
          { key: "reference", header: "Reference", render: (r) => r.reference || "Draft" },
          { key: "title", header: "Title" },
          { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
          { key: "open", header: "", align: "right", render: (r) => (
            <Button size="xs" variant="light" onClick={() => setOpen(r.application_id)}
              aria-label={`Open ${r.reference || r.title}`}>Open</Button>) },
        ]}
      />
      <ApplicationDrawer id={open} onClose={() => setOpen(null)} />
    </>
  );
}

// Applications within the caller's scope, searchable, each opening the drawer.
export function ApplicationsTable({ emptyTitle, emptyDescription }: {
  emptyTitle: string; emptyDescription?: string;
}) {
  const [q, setQ] = useState("");
  const list = useApplications(q ? { q } : undefined);
  const [open, setOpen] = useState<number | null>(null);
  return (
    <>
      <Group mb="sm">
        <TextInput label="Search by title or reference" value={q} w={320}
          onChange={(e) => setQ(e.currentTarget.value)} />
      </Group>
      {list.error ? <ErrorState error={list.error} /> : (
        <DataTable<ApplicationRow>
          rows={list.data?.results ?? []} loading={list.isPending} rowKey={(r) => r.id}
          empty={{ icon: FaInbox, title: emptyTitle, description: emptyDescription }}
          columns={[
            { key: "reference", header: "Reference", render: (r) => r.reference || "Draft" },
            { key: "title", header: "Title" },
            { key: "applicant_name", header: "Applicant" },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            { key: "updated_at", header: "Updated", render: (r) => day(r.updated_at) },
            { key: "open", header: "", align: "right", render: (r) => (
              <Button size="xs" variant="light" onClick={() => setOpen(r.id)}
                aria-label={`Open ${r.reference || r.title}`}>Open</Button>) },
          ]}
        />
      )}
      <ApplicationDrawer id={open} onClose={() => setOpen(null)} />
    </>
  );
}
