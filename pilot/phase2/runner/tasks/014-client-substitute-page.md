TITLE: Rewrite the Substitute Requests page
FORMAT: whole
EDIT: client/src/modules/leave/pages/SubstituteRequestsPage.tsx
READ: client/src/modules/leave/api.ts client/src/ui/components/DataTable.tsx client/src/ui/components/ErrorState.tsx kit:phase2/DESIGN.md
LIMIT: 1200
POST: none
---
Review findings: the Phase-1 page imports modules that do not exist and never calls the server.

Replace the whole file with a default-exported SubstituteRequestsPage component (EL-UC-011, BR-EL-014, BR-EL-015). Start it with these imports. tsconfig has noUnusedLocals, so remove any imported name you end up not using, and do not import from any other path:

import { Button, Card, Container, Group } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { CATEGORY_LABELS, useInbox, useSubstituteResponse, type LeaveApplication } from "../api";

Rows: useInbox() filtered to stage "substitute" (requests where a colleague nominated me as their substitute).
DataTable columns: Colleague (user_id), Category (CATEGORY_LABELS), Dates, Days, Purpose, Actions with "Accept" (accept true) and "Decline" (accept false) buttons that call useSubstituteResponse().mutate({ id, accept }).
Empty state title: "No substitute requests".
If useInbox() has an error, render <ErrorState error={error} />.

Fusion uses Mantine 7: use leftSection (not leftIcon), gap (not spacing), justify (not position), and the shared components in client/src/ui/components (read-only). DataTable needs the props rows, columns, loading, rowKey and empty ({ title, description }). Every mutation shows notifications.show({ color: "green", ... }) on success and notifications.show({ color: "red", title: "...", message: errorMessage(e) }) on error.

Write the whole file. Do not ask for more files.
