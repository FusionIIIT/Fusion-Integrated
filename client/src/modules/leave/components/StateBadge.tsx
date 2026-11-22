import { Badge } from "@mantine/core";

export function StateBadge({ status }: { status: string }) {
  const color = status === "approved" || status === "cancelled" ? "green"
    : status.includes("rejected") || status === "rejected" ? "red"
      : status === "withdrawn" ? "gray" : "blue";
  return <Badge color={color} variant="light">{status.replaceAll("_", " ")}</Badge>;
}
