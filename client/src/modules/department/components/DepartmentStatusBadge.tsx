import { Badge } from "@mantine/core";

const COLOR_MAP: Record<string, string> = {
  pending: "yellow",
  approved: "blue",
  issued: "green",
  rejected: "red",
  submitted: "gray",
  reviewed: "cyan",
  resolved: "teal",
  closed: "dark",
};

interface Props {
  status: string;
}

export function DepartmentStatusBadge({ status }: Props) {
  const color = COLOR_MAP[status.toLowerCase()] || "gray";
  return (
    <Badge color={color} variant="light" size="sm">
      {status}
    </Badge>
  );
}
