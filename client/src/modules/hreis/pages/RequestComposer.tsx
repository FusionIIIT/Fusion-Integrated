import { useState } from "react";
import { Alert, Button, Drawer, Group, Select, Stack, Text, Textarea, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import {
  useSubmitAppraisal, useSubmitClaim, useSubmitLeave,
} from "../api/hooks";
import type { LeaveInput } from "../api/types";

type Mode = "leave" | "ltc" | "cpda" | "appraisal" | null;

const leaveTypes: LeaveInput["leave_type"][] = [
  "Casual", "Restricted", "Medical", "Earned", "Vacation", "Sabbatical",
];

export function RequestComposer({ only }: { only?: "leave" | "claims" | "appraisal" }) {
  const { can } = useAuth();
  const [mode, setMode] = useState<Mode>(null);
  const [leaveType, setLeaveType] = useState<LeaveInput["leave_type"]>("Casual");
  const [duration, setDuration] = useState("");
  const [justification, setJustification] = useState("");
  const [subtype, setSubtype] = useState<"advance" | "reimbursement">("advance");
  const [formReference, setFormReference] = useState("");
  const [purpose, setPurpose] = useState("");
  const [amount, setAmount] = useState("");
  const [documents, setDocuments] = useState("");
  const [period, setPeriod] = useState("");
  const [appraisalForm, setAppraisalForm] = useState("{}");
  const leave = useSubmitLeave();
  const claim = useSubmitClaim();
  const appraisal = useSubmitAppraisal();
  const pending = leave.isPending || claim.isPending || appraisal.isPending;

  if (!can("hreis.leave.create") && !can("hreis.claim.create")
      && !can("hreis.appraisal.create")) {
    return null;
  }

  function showSuccess() {
    notifications.show({ title: "Request recorded", color: "green", position: "top-center",
      message: "Your submission is now visible in HR Requests." });
    setMode(null);
  }

  function showError(error: unknown) {
    notifications.show({ title: "Request could not be submitted", color: "red", position: "top-center",
      message: errorMessage(error) });
  }

  function submit() {
    if (mode === "leave") {
      leave.mutate({
        leave_type: leaveType, duration, justification,
      }, { onSuccess: showSuccess, onError: showError });
    } else if (mode === "ltc" || mode === "cpda") {
      const documentRefs = documents.split(",").map((item) => item.trim()).filter(Boolean);
      if (mode === "cpda" && (
        !purpose.trim() || !/^\d{1,14}(?:\.\d{1,6})?$/.test(amount.trim())
        || Number(amount) <= 0 || documentRefs.length === 0
      )) {
        notifications.show({
          color: "red", title: "Complete CPDA claim fields", position: "top-center",
          message: "Provide a purpose, positive amount and document references.",
        });
        return;
      }
      if (mode === "ltc" && !formReference.trim()) {
        notifications.show({
          color: "red", title: "Official LTC form required", position: "top-center",
          message: "Provide the prescribed LTC form reference.",
        });
        return;
      }
      claim.mutate({
        family: mode, subtype,
        prescribed_form_reference: mode === "ltc" ? formReference : undefined,
        purpose: mode === "cpda" ? purpose : undefined,
        amount: mode === "cpda" ? amount : undefined,
        document_references: mode === "cpda"
          ? documents.split(",").map((item) => item.trim()).filter(Boolean)
          : undefined,
      }, { onSuccess: showSuccess, onError: showError });
    } else if (mode === "appraisal") {
      try {
        const payload: unknown = JSON.parse(appraisalForm);
        if (!payload || typeof payload !== "object" || Array.isArray(payload)
            || Object.keys(payload).length === 0) {
          throw new Error("The appraisal form must be a nonempty JSON object.");
        }
        appraisal.mutate({
          period_key: period,
          submitted_form: payload as Record<string, unknown>,
        }, { onSuccess: showSuccess, onError: showError });
      } catch (error) {
        showError(error);
      }
    }
  }

  return (
    <>
      <Group gap="sm" mb="lg" wrap="wrap">
        {(!only || only === "leave") && can("hreis.leave.create")
          && <Button onClick={() => setMode("leave")}>
          Apply for leave
        </Button>}
        {(!only || only === "claims") && can("hreis.claim.create") && <>
          <Button variant="light" onClick={() => setMode("ltc")}>LTC request</Button>
          <Button variant="light" onClick={() => setMode("cpda")}>CPDA request</Button>
        </>}
        {(!only || only === "appraisal") && can("hreis.appraisal.create")
          && <Button variant="light"
          onClick={() => setMode("appraisal")}>Annual appraisal</Button>}
      </Group>
      <Drawer opened={mode !== null} onClose={() => !pending && setMode(null)}
        title={mode ? `New ${mode.toUpperCase()} request` : ""} position="right" size="lg">
        <Stack gap="md">
          <Alert color="blue" title="Institutional policy applies">
            Your submission is checked against the active HR policy. Missing
            quotas, approval routes or submission windows are never assumed.
          </Alert>
          {mode === "leave" && <>
            <Select label="Leave type" required data={leaveTypes}
              value={leaveType} onChange={(value) => setLeaveType(
                leaveTypes.find((item) => item === value) ?? "Casual")} />
            <TextInput label="Duration (days)" required value={duration}
              onChange={(event) => setDuration(event.currentTarget.value)} />
            <Textarea label="Justification" required autosize minRows={3}
              value={justification}
              onChange={(event) => setJustification(event.currentTarget.value)} />
          </>}
          {(mode === "ltc" || mode === "cpda") && <>
            <Select label="Request kind" required value={subtype}
              data={[
                { value: "advance", label: "Advance" },
                { value: "reimbursement", label: "Reimbursement" },
              ]}
              onChange={(value) =>
                setSubtype(value === "reimbursement" ? "reimbursement" : "advance")} />
            {mode === "ltc" ? <TextInput label="Official LTC form reference"
              required value={formReference}
              onChange={(event) => setFormReference(event.currentTarget.value)} />
              : <>
                <Textarea label="Purpose" required autosize minRows={2}
                  value={purpose}
                  onChange={(event) => setPurpose(event.currentTarget.value)} />
                <TextInput label="Claim amount" required value={amount}
                  onChange={(event) => setAmount(event.currentTarget.value)} />
                <Textarea label="Document references (comma-separated)" required
                  autosize minRows={2} value={documents}
                  onChange={(event) => setDocuments(event.currentTarget.value)} />
              </>}
            <Text size="xs" c="dimmed">
              References are not file uploads. The claim remains awaiting HR
              verification; no document is marked verified automatically.
            </Text>
          </>}
          {mode === "appraisal" && <>
            <TextInput label="Appraisal period" required value={period}
              onChange={(event) => setPeriod(event.currentTarget.value)} />
            <Textarea label="Completed appraisal form (JSON object)" required
              autosize minRows={6} value={appraisalForm}
              onChange={(event) => setAppraisalForm(event.currentTarget.value)} />
          </>}
          <Group justify="flex-end">
            <Button variant="default" disabled={pending} onClick={() => setMode(null)}>
              Cancel
            </Button>
            <Button loading={pending} onClick={submit}>Submit request</Button>
          </Group>
        </Stack>
      </Drawer>
    </>
  );
}
