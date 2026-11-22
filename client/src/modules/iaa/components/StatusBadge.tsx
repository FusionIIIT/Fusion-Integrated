import { Badge } from "@mantine/core";

const COLOR_MAP: Record<string, string> = {
  draft: "gray",
  submitted: "blue",
  query_raised: "orange",
  query_responded: "cyan",
  finance_validated: "indigo",
  approval_pending: "yellow",
  verified: "teal",
  approved: "green",
  rejected: "red",
  escalated: "pink",
  recorded: "violet",
  open: "orange",
  resolved: "green",
  closed: "gray",
};

export function StatusBadge({ status }: { status: string }) {
  const color = COLOR_MAP[status.toLowerCase()] || "gray";
  const label = status.replace(/_/g, " ").toUpperCase();
  return <Badge color={color} variant="filled">{label}</Badge>;
}
