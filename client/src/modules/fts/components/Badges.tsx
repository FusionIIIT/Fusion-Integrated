import { Badge } from "@mantine/core";

import type { FileStatus, Priority } from "../api/types";
import { STATUS_COLOR, STATUS_LABEL } from "../lib/rules";

export function FileStatusBadge({ status }: { status: FileStatus }) {
  return (
    <Badge color={STATUS_COLOR[status] ?? "gray"} variant="light">
      {STATUS_LABEL[status] ?? status}
    </Badge>
  );
}

const PRIORITY_COLOR: Record<Priority, string> = {
  low: "gray", medium: "blue", high: "orange", urgent: "red",
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <Badge color={PRIORITY_COLOR[priority] ?? "gray"} variant="dot">
      {priority}
    </Badge>
  );
}
