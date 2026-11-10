import { Link } from "react-router-dom";
import { Anchor, Text } from "@mantine/core";

import type { Column } from "../../../ui/components/DataTable";
import { DataTable } from "../../../ui/components/DataTable";
import type { FileSummary } from "../api/types";
import { formatTime } from "../lib/format";
import { FileStatusBadge, PriorityBadge } from "./Badges";

const COLUMNS: Column<FileSummary>[] = [
  { key: "uin", header: "File no.", render: (f) => (
      <Anchor component={Link} to={`/fts/files/${f.id}`} fw={600}>{f.uin}</Anchor>
  ) },
  { key: "subject", header: "Subject", render: (f) => <Text>{f.subject}</Text> },
  { key: "priority", header: "Priority", render: (f) => <PriorityBadge priority={f.priority} /> },
  { key: "category", header: "Category" },
  { key: "status", header: "Status", render: (f) => <FileStatusBadge status={f.status} /> },
  { key: "creator_id", header: "Created by" },
  { key: "current_holder_id", header: "Held by" },
  { key: "updated_at", header: "Updated", render: (f) => formatTime(f.updated_at) },
];

export function FileRows({ rows, loading, emptyTitle, emptyDescription }: {
  rows: FileSummary[];
  loading: boolean;
  emptyTitle: string;
  emptyDescription: string;
}) {
  return (
    <DataTable
      rows={rows} columns={COLUMNS} loading={loading}
      rowKey={(f) => f.id}
      empty={{ title: emptyTitle, description: emptyDescription }}
    />
  );
}

export default FileRows;
