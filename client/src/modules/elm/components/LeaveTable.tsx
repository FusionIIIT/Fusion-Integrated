import { Group, Text } from "@mantine/core";
import { FaCalendarAlt } from "react-icons/fa";

import { DataTable, type Column } from "../../../ui/components/DataTable";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { LeaveRequest } from "../api/types";

export function LeaveTable({ rows, loading, actions, showApplicant, empty }: {
  rows: LeaveRequest[];
  loading: boolean;
  actions?: (r: LeaveRequest) => React.ReactNode;
  showApplicant?: boolean;
  empty: { title: string; description?: string };
}) {
  const columns: Column<LeaveRequest>[] = [
    { key: "id", header: "#", render: (r) => <Text size="sm">{r.id}</Text> },
    ...(showApplicant ? [{
      key: "applicant", header: "Applicant",
      render: (r: LeaveRequest) => (
        <Text size="sm">{r.applicant_name || r.user_id}
          <Text span c="dimmed" size="xs"> {r.applicant_unit}</Text></Text>),
    }] : []),
    { key: "category", header: "Leave",
      render: (r) => (
        <Text size="sm">{r.category_label}{r.kind === "extension" ? " (extension)" : ""}
          {r.half ? ` · ${r.half} half` : ""}</Text>) },
    { key: "period", header: "Period",
      render: (r) => <Text size="sm">{r.start_date} → {r.end_date} ({r.days} d)</Text> },
    { key: "status", header: "Status",
      render: (r) => (
        <Group gap={6}>
          <StatusBadge status={r.status} />
          {r.current_role && <Text size="xs" c="dimmed">at {r.current_role}</Text>}
          {r.recommendation && (
            <Text size="xs" c="dimmed">{r.recommendation.replace("_", " ")}</Text>)}
        </Group>) },
    ...(actions ? [{ key: "actions", header: "", align: "right" as const,
      render: (r: LeaveRequest) => <Group gap={6} justify="flex-end">{actions(r)}</Group> }]
      : []),
  ];
  return (
    <DataTable
      rows={rows} columns={columns} loading={loading} rowKey={(r) => r.id}
      empty={{ icon: FaCalendarAlt, ...empty }}
    />
  );
}
