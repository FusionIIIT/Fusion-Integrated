import { Badge } from "@mantine/core";
import React from "react";
import type { LeaveStatus } from "../types";

const STATUS_COLORS: Record<LeaveStatus, string> = {
  DRAFT: "gray",
  PENDING_SUBSTITUTE: "blue",
  SUBSTITUTE_DECLINED: "red",
  PENDING_UNIT_HEAD: "yellow",
  PENDING_ESTABLISHMENT: "violet",
  PENDING_SANCTION: "orange",
  APPROVED: "teal",
  REJECTED: "red",
  WITHDRAWN: "gray",
  CANCEL_REQUESTED: "orange",
  CANCELLED: "dark",
  EXT_REQUESTED: "cyan",
  RESUMED: "indigo",
  RESUMPTION_REVIEWED: "teal",
};

export const LeaveStatusBadge: React.FC<{ status: LeaveStatus }> = ({ status }) => {
  const color = STATUS_COLORS[status] || "gray";
  const label = status.replace(/_/g, " ");
  return (
    <Badge color={color} variant="light" size="sm">
      {label}
    </Badge>
  );
};
