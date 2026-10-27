TITLE: Rewrite the Approvals page (Unit Head, Establishment, Sanctioning Authority)
FORMAT: whole
EDIT: client/src/modules/leave/pages/ApprovalsPage.tsx
READ: client/src/modules/leave/api.ts client/src/ui/components/DataTable.tsx client/src/ui/components/StatusBadge.tsx client/src/ui/components/ErrorState.tsx kit:phase2/DESIGN.md
LIMIT: 1500
POST: none
---
Review findings: the Phase-1 page imports modules that do not exist and shows every application with approve/reject buttons regardless of who the approver is or which stage the request is in.

Replace the whole file with a default-exported ApprovalsPage component (EL-UC-003, EL-UC-004, EL-UC-005, EL-UC-006). Start it with these imports. tsconfig has noUnusedLocals, so remove any imported name you end up not using, and do not import from any other path:

import { useState } from "react";
import { Button, Card, Container, Group, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { CATEGORY_LABELS, useDecide, useInbox, type Decision, type LeaveApplication } from "../api";

Rows: useInbox() filtered to stage other than "substitute" (the server already returns only requests assigned to me).
A TextInput "Remark (optional)" above the table; its value is sent with the next decision and cleared after success.
DataTable columns: Applicant (user_id), Category (CATEGORY_LABELS, plus " (cancellation)" when kind is "cancellation"), Dates, Days, Purpose, Stage, Unit Head recommendation, Actions.
Actions depend on the stage (DESIGN.md "Workflow"):
- stage "unit_head" and category "CL" or "RH": "Approve" (decision "approve") and "Reject" ("reject");
- stage "unit_head" and any other category: "Recommend" ("recommended") and "Not recommended" ("not_recommended");
- stage "establishment": "Verify" ("verify");
- stage "sanction": "Approve" ("approve") and "Reject" ("reject").
Each button calls useDecide().mutate({ id, decision, remark }). Use a helper function actionsFor(row: LeaveApplication): { label: string; decision: Decision; color: string }[] to keep the render small.
If useInbox() has an error, render <ErrorState error={error} />.

Fusion uses Mantine 7: use leftSection (not leftIcon), gap (not spacing), justify (not position), and the shared components in client/src/ui/components (read-only). DataTable needs the props rows, columns, loading, rowKey and empty ({ title, description }). Every mutation shows notifications.show({ color: "green", ... }) on success and notifications.show({ color: "red", title: "...", message: errorMessage(e) }) on error.

Write the whole file. Do not ask for more files.
