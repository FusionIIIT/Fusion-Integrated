import { Badge, Group } from "@mantine/core";
import type { ComplaintStatus } from "../api/types";

interface Props {
  status: ComplaintStatus;
  isEscalated?: boolean;
}

const COLOR_MAP: Record<ComplaintStatus, string> = {
  submitted: "blue",
  in_progress: "yellow",
  resolved: "teal",
  rejected: "red",
  closed: "gray",
};

const LABEL_MAP: Record<ComplaintStatus, string> = {
  submitted: "Submitted",
  in_progress: "In Progress",
  resolved: "Resolved",
  rejected: "Rejected",
  closed: "Closed",
};

export function StatusBadge({ status, isEscalated }: Props) {
  return (
    <Group gap={4} wrap="nowrap">
      <Badge color={COLOR_MAP[status] || "gray"} variant="filled" size="sm">
        {LABEL_MAP[status] || status}
      </Badge>
      {isEscalated && (
        <Badge color="red" variant="outline" size="xs">
          Escalated
        </Badge>
      )}
    </Group>
  );
}
