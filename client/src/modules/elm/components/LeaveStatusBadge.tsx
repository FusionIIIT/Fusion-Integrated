import { Badge } from "@mantine/core";

/** One status→colour map for this module, so a status is never two colours. */
const COLORS: Record<string, string> = {
  pending: "orange",
  approved: "green",
  rejected: "red",
  withdrawn: "gray",
  cancelled: "gray",
};

export function LeaveStatusBadge({ status }: { status: string }) {
  return (
    <Badge color={COLORS[status] ?? "gray"} variant="light" size="sm">
      {status}
    </Badge>
  );
}
