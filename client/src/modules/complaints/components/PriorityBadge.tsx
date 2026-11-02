import { Badge } from "@mantine/core";
import type { ComplaintPriority } from "../api/types";

interface Props {
  priority: ComplaintPriority;
}

const COLOR_MAP: Record<ComplaintPriority, string> = {
  high: "red",
  medium: "orange",
  low: "blue",
};

export function PriorityBadge({ priority }: Props) {
  return (
    <Badge color={COLOR_MAP[priority] || "gray"} variant="light" size="sm">
      {priority ? priority.toUpperCase() : "MEDIUM"}
    </Badge>
  );
}
