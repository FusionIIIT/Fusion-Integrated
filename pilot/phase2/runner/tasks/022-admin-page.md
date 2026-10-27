TITLE: Add the Reporting Lines admin page for the Leave Administrator (EL-UC-014)
FORMAT: whole
EDIT: client/src/modules/leave/pages/ReportingLinesPage.tsx
READ: client/src/modules/leave/api.ts client/src/modules/leave/pages/ApplyLeavePage.tsx
LIMIT: 1200
POST: none
---
Create a new file client/src/modules/leave/pages/ReportingLinesPage.tsx: a default-exported ReportingLinesPage component where the Leave Administrator looks up a person by user id and sets who decides their leave. Follow the style of ApplyLeavePage.tsx (read-only). Use exactly these imports:

import { useState } from "react";
import { Button, Card, Container, Group, NumberInput, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage, errorStatus } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReportingLine, useSetReportingLine } from "../api";

Behaviour:
- State: lookupId (string, the NumberInput value), userId (number | null, set by a "Load" button from lookupId), unitHeadId, establishmentId, sanctioningId (strings).
- const line = useReportingLine(userId); const save = useSetReportingLine();
- When line.data arrives, copy its three ids into the three inputs (do it in the Load button's flow by calling line.refetch() and, in its .then, setting the state from the result's data; empty string for null).
- If line.error has errorStatus(line.error) === 404, show <Text c="dimmed">No reporting line yet for user {userId}. Fill in the fields below and save.</Text>.
- Three NumberInputs: "Unit Head (user id)" (required), "Establishment officer (user id, optional)", "Sanctioning Authority (user id, optional)". Each onChange={(v) => setX(String(v))}.
- A "Save" Button (disabled until userId and unitHeadId are set, loading={save.isPending}) calls save.mutate({ user_id: userId, unit_head_id: Number(unitHeadId), establishment_id: establishmentId ? Number(establishmentId) : null, sanctioning_authority_id: sanctioningId ? Number(sanctioningId) : null }) with onSuccess -> notifications.show({ color: "green", title: "Saved", message: `Reporting line for user ${userId} saved.` }) and onError -> notifications.show({ color: "red", title: "Could not save", message: errorMessage(e) }).
- Layout: <Container size="sm"> with <PageHeader title="Reporting Lines" subtitle="Who decides each person's leave" />, then a Card with a Group (lookup NumberInput "User id" + "Load" Button), then a Stack with the three inputs and the Save button.
tsconfig has noUnusedLocals, so remove any import you end up not using. Write the whole file. Do not ask for more files.
