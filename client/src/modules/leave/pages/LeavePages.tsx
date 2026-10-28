import { Stack, Text, Title } from "@mantine/core";

/** ELM pages. Kept intentionally small in this pilot: the point is that the
 *  module integrates with the existing shell, sidebar and RBAC, not a bespoke
 *  design. Real data wiring lives in ./api. */
function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <Stack gap="xs">
      <Title order={2}>{title}</Title>
      <Text c="dimmed">{note}</Text>
    </Stack>
  );
}

export function MyLeavePage() {
  return (
    <Placeholder
      title="My Leave"
      note="Apply for CL, RH, SCL, EL, COL or VL, and track each request's status."
    />
  );
}

export function BalancesPage() {
  return (
    <Placeholder
      title="My Balances"
      note="Entitlement, carried-forward and availed days per category."
    />
  );
}

export function SubstitutePage() {
  return (
    <Placeholder
      title="Cover Requests"
      note="Accept or decline responsibility coverage you have been nominated for."
    />
  );
}

export function QueuePage() {
  return (
    <Placeholder
      title="Approval Queue"
      note="Review and record Recommended / Not Recommended, or give the final sanction."
    />
  );
}

export function CalendarPage() {
  return (
    <Placeholder
      title="Calendar"
      note="Maintain the published holiday and restricted-holiday calendar."
    />
  );
}

export function PolicyPage() {
  return (
    <Placeholder
      title="Policy"
      note="Leave-policy parameters used for validation and entitlement."
    />
  );
}

export function ReportsPage() {
  return (
    <Placeholder
      title="Reports"
      note="Leave usage by category and status across the organisation."
    />
  );
}
