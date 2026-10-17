import { Stack, Text } from "@mantine/core";

import type { Column } from "../../../ui/components/DataTable";
import { CATEGORY_LABELS, type LeaveRequest } from "../api/types";

function period(r: LeaveRequest) {
  if (r.half) return `${r.start_date} (${r.half} half)`;
  return r.start_date === r.end_date ? r.start_date : `${r.start_date} → ${r.end_date}`;
}

/** Columns shared by the applicant's and the reviewer's tables. */
export const leaveColumns: Column<LeaveRequest>[] = [
  {
    key: "category", header: "Leave",
    render: (r) => (
      <Stack gap={0}>
        <Text fw={600}>{CATEGORY_LABELS[r.category]}</Text>
        {r.is_station_leave && <Text size="xs" c="dimmed">with Station Leave</Text>}
      </Stack>
    ),
  },
  { key: "period", header: "Period", render: period },
  { key: "days", header: "Days", render: (r) => r.days },
  {
    key: "reason", header: "Reason",
    render: (r) => <Text size="sm" lineClamp={2}>{r.reason}</Text>,
  },
];
