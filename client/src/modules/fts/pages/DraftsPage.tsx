import { Link } from "react-router-dom";
import { Anchor, Button } from "@mantine/core";

import type { Column } from "../../../ui/components/DataTable";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useDrafts } from "../api/hooks";
import type { DraftSummary } from "../api/types";
import { FileStatusBadge, PriorityBadge } from "../components/Badges";
import { FtsError } from "../components/FtsError";
import { formatTime } from "../lib/format";

const COLUMNS: Column<DraftSummary>[] = [
  { key: "uin", header: "File no.", render: (f) => (
      <Anchor component={Link} to={`/fts/files/${f.id}`} fw={600}>{f.uin}</Anchor>
  ) },
  { key: "subject", header: "Subject" },
  { key: "priority", header: "Priority", render: (f) => <PriorityBadge priority={f.priority} /> },
  { key: "category", header: "Category" },
  { key: "status", header: "Status", render: (f) => <FileStatusBadge status={f.status} /> },
  { key: "updated_at", header: "Saved", render: (f) => formatTime(f.updated_at) },
];

export function DraftsPage() {
  const { data, isPending, error } = useDrafts();
  return (
    <>
      <PageHeader
        title="Drafts" subtitle="Files you saved but have not sent yet"
        action={<Button component={Link} to="/fts/new">New file</Button>}
      />
      {error != null ? <FtsError error={error} /> : (
        <DataTable
          rows={data ?? []} columns={COLUMNS} loading={isPending}
          rowKey={(f) => f.id}
          empty={{ title: "No drafts", description: "Saved drafts appear here until you send them." }}
        />
      )}
    </>
  );
}

export default DraftsPage;
