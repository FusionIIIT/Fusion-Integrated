import { Badge } from "@mantine/core";

const STATUS_COLORS: Record<string, string> = {
  draft: "gray",
  submitted: "blue",
  rejected: "red",
  hod_approved: "cyan",
  policy_applied: "green",
  routed_to_security: "orange",
  encryption_configured: "indigo",
  encrypted_archive_created: "teal",
  routine: "gray",
  sensitive: "orange",
  critical: "red",
  archival: "purple",
};

export function BadmsStatusBadge({
  value,
  variant = "light",
}: {
  value: string;
  variant?: "light" | "filled" | "outline";
}) {
  const color = STATUS_COLORS[value.toLowerCase()] || "gray";
  const label = value.replace(/_/g, " ").toUpperCase();
  return (
    <Badge color={color} variant={variant} size="sm">
      {label}
    </Badge>
  );
}
