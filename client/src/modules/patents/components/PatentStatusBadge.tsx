import { Badge } from "@mantine/core";
import type { PatentApplicationStatus } from "../api/types";

const COLORS: Record<string, string> = {
  DRAFT: "gray",
  SUBMITTED: "blue",
  DIRECTOR_ASSIGNED: "cyan",
  UNDER_REVIEW: "indigo",
  NEEDS_REVISION: "orange",
  RESUBMITTED: "blue",
  APPROVED: "teal",
  REJECTED: "red",
  APPEAL_SUBMITTED: "violet",
  APPEALED: "violet",
  DECISION_MODIFIED: "teal",
  ATTORNEY_ASSIGNED: "grape",
  PENDING_REVIEW: "yellow",
  ASSESSMENT_IN_PROGRESS: "indigo",
  BUDGET_PENDING: "pink",
  FILED: "blue",
  OFFICE_ACTION_PENDING: "orange",
  RESPONSE_SUBMITTED: "cyan",
  GRANTED: "green",
  WITHDRAWN: "gray",
  ABANDONED: "gray",
  EXPIRED: "gray",
};

export function PatentStatusBadge({ status }: { status: PatentApplicationStatus | string }) {
  const color = COLORS[status] ?? "gray";
  return (
    <Badge color={color} variant="light" size="sm">
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
