import { Badge } from "@mantine/core";

/** One status→colour map, so the same status is never two colours. */
const COLORS: Record<string, string> = {
  draft: "gray",
  submitted: "blue",
  under_review: "indigo",
  shortlisted: "violet",
  offer_issued: "orange",
  offer_accepted: "green",
  offer_declined: "gray",
  rejected: "red",
  withdrawn: "gray",
  published: "green",
  closed: "gray",
  cancelled: "red",
  active: "green",
  approved: "teal",
  forwarded: "cyan",
  pending: "yellow",
  pending_approval: "yellow",
  pending_verification: "orange",
  verified: "blue",
  returned: "orange",
  settled: "teal",
  paid: "teal",
  unpaid: "gray",
  processing: "blue",
  retired: "gray",
  resigned: "gray",
  finalized: "teal",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge color={COLORS[status] ?? "gray"} variant="light" size="sm">
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
