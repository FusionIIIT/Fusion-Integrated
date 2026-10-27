TITLE: Rewrite the My Leaves page (balances, history, withdraw, cancel, replace substitute)
FORMAT: whole
EDIT: client/src/modules/leave/pages/MyLeavesPage.tsx
READ: client/src/modules/leave/api.ts client/src/ui/components/DataTable.tsx client/src/ui/components/StatusBadge.tsx client/src/ui/components/ErrorState.tsx kit:phase2/DESIGN.md
LIMIT: 1500
POST: none
---
Review findings: the Phase-1 page imports "../api/hooks", "../api/types" and "../components/HistoryDrawer", which do not exist, and its Withdraw and Cancel buttons only show a notification without calling the server.

Replace the whole file with a default-exported MyLeavesPage component (EL-UC-002, EL-UC-007, EL-UC-008, BR-EL-015). Start it with these imports. tsconfig has noUnusedLocals, so remove any imported name you end up not using, and do not import from any other path:

import { useState } from "react";
import { Button, Card, Container, Group, NumberInput, SimpleGrid, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  CATEGORY_LABELS, useBalances, useCancel, useMyApplications, useReplaceSubstitute, useWithdraw,
  type LeaveApplication,
} from "../api";

Layout:
1. PageHeader "My Leaves".
2. A SimpleGrid of small Cards, one per balance from useBalances(new Date().getFullYear()): the category label, "available of entitled days", and "used".
3. A Card with a DataTable<LeaveApplication> of useMyApplications() rows. Columns: Category (CATEGORY_LABELS, plus " (cancellation)" when kind is "cancellation"), Dates (start_date to end_date), Days, Stage, Status (StatusBadge), Substitute, Actions.
   - Actions: a "Withdraw" button when status is "pending" and kind is "leave" (useWithdraw); a "Cancel leave" button when status is "approved", kind is "leave" and start_date is after today's date as "YYYY-MM-DD" (useCancel).
   - Substitute column: when substitute_status is "declined" and status is "pending", render a small ReplaceSubstitute component defined in this file: it keeps its own useState for the new user id and shows a NumberInput (size "xs") and a "Nominate" button that calls useReplaceSubstitute().mutate({ id, substitute_id }). Otherwise show substitute_id and substitute_status, or "-".
If useMyApplications() has an error, render <ErrorState error={error} /> inside the Container.

Fusion uses Mantine 7: use leftSection (not leftIcon), gap (not spacing), justify (not position), and the shared components in client/src/ui/components (read-only). DataTable needs the props rows, columns, loading, rowKey and empty ({ title, description }). Every mutation shows notifications.show({ color: "green", ... }) on success and notifications.show({ color: "red", title: "...", message: errorMessage(e) }) on error.

Write the whole file. Do not ask for more files.
