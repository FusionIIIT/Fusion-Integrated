import { Badge } from "@mantine/core";

/** One status→colour map, so the same status is never two colours. */
const COLORS: Record<string, string> = {
  draft: "gray", submitted: "blue", under_review: "indigo",
  shortlisted: "violet", offer_issued: "orange", offer_accepted: "green",
  offer_declined: "gray", rejected: "red", withdrawn: "gray",
  published: "green", closed: "gray", cancelled: "red", active: "green",
  deactivated: "orange", suspended: "orange", archived: "gray",
  reversible: "yellow", permanent_non_restorable: "dark", restored: "teal",
  pending_it_head: "yellow", approved: "blue", purged: "red",
  scheduled: "cyan", expired: "gray", revoked: "red", extended: "indigo",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge color={COLORS[status] ?? "gray"} variant="light" size="sm">
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
