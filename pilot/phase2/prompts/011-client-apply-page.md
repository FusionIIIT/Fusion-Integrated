Review findings: the Phase-1 page imports "../api/hooks" and "../api/types", which do not exist (TypeScript fails), offers categories the institute does not have ("sick", "personal"), and never sends the request.

Replace the whole file with a default-exported ApplyLeavePage component (EL-UC-001). Start it with these imports. tsconfig has noUnusedLocals, so remove any imported name you end up not using, and do not import from any other path:

import { useState } from "react";
import { Button, Card, Checkbox, Container, Group, NumberInput, Select, Stack, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { CATEGORY_LABELS, useApply, type HalfDay, type LeaveCategory } from "../api";

Form (plain useState, no form library): category Select (data built from CATEGORY_LABELS, default "CL"); start_date and end_date as TextInput type="date"; half_day Select ("none" Full day, "first" First half, "second" Second half) shown only when category is "CL" and start_date equals end_date, otherwise sent as "none"; purpose Textarea (required); station_leave Checkbox ("I will leave the station"); station_address Textarea shown only when station_leave is checked; substitute_id NumberInput (optional, label "Substitute (user id)", empty means null).
Submit calls useApply().mutate({ category, start_date, end_date, half_day, purpose, station_leave, station_address, substitute_id }) and on success shows a notification and navigates to "/leave/mine". The submit Button has loading={apply.isPending} and is disabled until category, both dates and purpose are filled.

Fusion uses Mantine 7: use leftSection (not leftIcon), gap (not spacing), justify (not position), and the shared components in client/src/ui/components (read-only). DataTable needs the props rows, columns, loading, rowKey and empty ({ title, description }). Every mutation shows notifications.show({ color: "green", ... }) on success and notifications.show({ color: "red", title: "...", message: errorMessage(e) }) on error.

Write the whole file. Do not ask for more files.
