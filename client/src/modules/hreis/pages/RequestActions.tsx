import { useState } from "react";
import {
  Alert, Button, Checkbox, Drawer, Group, Select, Stack, Text, Textarea, TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import {
  useAssignReviewers, useDecideAppraisal, useDecideRequest,
  useRecordFinancialProcessing, useVerifyClaim, useVerifyFinancialCorrectness,
} from "../api/hooks";
import type { HRRequest } from "../api/types";

type ActionMode =
  "verify" | "assign" | "decision" | "appraisal" | "finance"
  | "financial_review" | null;

export function RequestActions({ request }: { request: HRRequest }) {
  const { can } = useAuth();
  const [mode, setMode] = useState<ActionMode>(null);
  const [decision, setDecision] = useState<"approve" | "reject" | "forward">("forward");
  const [reason, setReason] = useState("");
  const [documentEvidence, setDocumentEvidence] = useState("");
  const [eligibilityBasis, setEligibilityBasis] = useState("");
  const [reviewers, setReviewers] = useState("");
  const [financialEvidence, setFinancialEvidence] = useState("");
  const [sourceSystem, setSourceSystem] = useState<"finance" | "payroll">("finance");
  const [statusReference, setStatusReference] = useState("");
  const [externalStatusAvailable, setExternalStatusAvailable] = useState(true);
  const [paymentStatus, setPaymentStatus] =
    useState<"processing" | "payment_pending" | "paid" | "failed">("payment_pending");
  const verifyClaim = useVerifyClaim();
  const decide = useDecideRequest();
  const assign = useAssignReviewers();
  const review = useDecideAppraisal();
  const finance = useRecordFinancialProcessing();
  const financeReview = useVerifyFinancialCorrectness();
  const pending = verifyClaim.isPending || decide.isPending
    || assign.isPending || review.isPending || finance.isPending
    || financeReview.isPending;
  const canVerify = (request.family === "ltc" || request.family === "cpda")
    && request.state === "awaiting_hr_verification" && can("hreis.claim.review");
  const canAssign = request.family === "appraisal"
    && request.state === "submitted" && can("hreis.appraisal.assign");
  const canDecide = (request.family === "leave" || request.family === "ltc"
    || request.family === "cpda") && request.state === "pending_authority"
    && can(request.family === "leave"
      ? "hreis.leave.approve" : "hreis.claim.approve");
  const canReview = request.family === "appraisal"
    && ["pending_review", "pending_next_appraisal_authority"].includes(request.state)
    && can("hreis.appraisal.approve");
  const isFinalAuthority = request.route_total_steps > 0
    && request.route_step === request.route_total_steps - 1;
  const appraisalEvent = isFinalAuthority ? "finalize" : "forward";
  const availableDecisions: Array<"approve" | "reject" | "forward"> =
    request.route_total_steps <= 0 ? ["reject"]
      : isFinalAuthority ? ["approve", "reject"] : ["forward", "reject"];
  const selectedDecision = availableDecisions.includes(decision)
    ? decision : (availableDecisions[0] ?? "reject");
  const canReviewFinance = ["ltc", "cpda"].includes(request.family)
    && request.state === "approved" && can("hreis.finance.review");
  const canRecordFinance = ["ltc", "cpda"].includes(request.family)
    && (
      request.state === "approved"
      || (request.state === "financial_processing_recorded"
        && !["paid", "failed"].includes(request.claim_summary?.payment_status ?? ""))
    ) && can("hreis.finance.update");

  if (
    !canVerify && !canAssign && !canDecide && !canReview
    && !canRecordFinance && !canReviewFinance
  ) return null;

  const actionMode: ActionMode = canVerify ? "verify"
    : canAssign ? "assign" : canDecide ? "decision"
      : canReview ? "appraisal" : canRecordFinance ? "finance" : "financial_review";

  const success = () => {
    notifications.show({ title: "Workflow updated", color: "green", position: "top-center",
      message: "The decision was recorded with its audit event." });
    setMode(null);
  };
  const failure = (error: unknown) => notifications.show({
    title: "Unable to update request", color: "red", position: "top-center",
    message: errorMessage(error),
  });

  function submit() {
    if (mode === "verify") {
      verifyClaim.mutate({
        id: request.id, document_review_reference: documentEvidence,
        eligibility_basis: eligibilityBasis,
      }, { onSuccess: success, onError: failure });
    } else if (mode === "assign") {
      const ids = reviewers.split(",").map((value) => Number(value.trim()));
      assign.mutate({ id: request.id, reviewer_user_ids: ids },
        { onSuccess: success, onError: failure });
    } else if (mode === "decision") {
      decide.mutate({ id: request.id, event: selectedDecision, reason },
        { onSuccess: success, onError: failure });
    } else if (mode === "appraisal") {
      review.mutate({ id: request.id, event: appraisalEvent },
        { onSuccess: success, onError: failure });
    } else if (mode === "financial_review") {
      financeReview.mutate({
        id: request.id,
        financial_review_reference: financialEvidence,
      }, { onSuccess: success, onError: failure });
    } else if (mode === "finance") {
      finance.mutate({
        id: request.id,
        financial_review_reference: financialEvidence,
        ...(externalStatusAvailable ? {
          source_system: sourceSystem, external_status_reference: statusReference,
          payment_status: paymentStatus,
        } : {}),
      }, { onSuccess: success, onError: failure });
    }
  }

  return (
    <>
      <Group gap="xs" wrap="wrap">
        <Button size="xs" variant="light" onClick={() => setMode(actionMode)}>
          {canVerify ? "Verify claim" : canAssign ? "Assign reviewers"
            : canRecordFinance ? "Record finance status"
              : canReviewFinance ? "Verify financial correctness" : "Review"}
        </Button>
        {canReviewFinance && canRecordFinance && (
          <Button size="xs" variant="light" onClick={() => setMode("financial_review")}>
            Verify financial correctness
          </Button>
        )}
      </Group>
      <Drawer opened={mode !== null} onClose={() => !pending && setMode(null)}
        title={`HR request #${request.id}`} size="lg" position="right">
        <Stack>
          <Text fw={600}>{request.family.toUpperCase()} — {request.state.replaceAll("_", " ")}</Text>
          <Alert color="blue" title="Official request evidence">
            Review the original submitted information before recording any decision.
            The API checks your current active role and assigned approval step.
          </Alert>
          <Text size="sm" c="dimmed">Submitted fields</Text>
          <Text size="sm" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
            {JSON.stringify(request.payload, null, 2)}
          </Text>
          {request.claim_summary && <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
            {JSON.stringify(request.claim_summary, null, 2)}
          </Text>}
          {request.appraisal_summary && <>
            <Text fw={600}>Submitted appraisal form</Text>
            <Text size="sm" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>
              {JSON.stringify(request.appraisal_summary.submitted_form, null, 2)}
            </Text>
          </>}
          {mode === "verify" && <>
            <Alert color="yellow" title="Human HR verification">
              This operation records your manual documentary and eligibility
              attestation. It does not perform an automated document check.
            </Alert>
            <TextInput label="Document review evidence reference" required
              value={documentEvidence}
              onChange={(event) => setDocumentEvidence(event.currentTarget.value)} />
            <Textarea label="Eligibility basis" required autosize minRows={3}
              value={eligibilityBasis}
              onChange={(event) => setEligibilityBasis(event.currentTarget.value)} />
          </>}
          {mode === "assign" && <TextInput
            label="Verified reviewer directory IDs (comma-separated)" required
            value={reviewers}
            onChange={(event) => setReviewers(event.currentTarget.value)} />}
          {mode === "decision" && <>
            <Select label="Authority decision" required value={selectedDecision}
              data={availableDecisions.map((option) => ({
                value: option, label: option === "forward"
                  ? "Forward to next authority"
                  : option === "approve" ? "Approve at final authority" : "Reject with reason",
              }))}
              onChange={(value) =>
                setDecision(value === "reject" ? "reject"
                  : value === "forward" ? "forward" : "approve")} />
            <Textarea label="Decision reason (required for rejection)"
              autosize minRows={3} value={reason}
              onChange={(event) => setReason(event.currentTarget.value)} />
          </>}
          {mode === "financial_review" && <>
            <Alert color="yellow" title="Independent financial correctness review">
              Record your manual financial assessment against the approved,
              HR-verified claim. This does not change payment status or send money.
            </Alert>
            <TextInput label="Financial review evidence reference" required
              value={financialEvidence}
              onChange={(event) => setFinancialEvidence(event.currentTarget.value)} />
          </>}
          {mode === "finance" && <>
            <Alert color="yellow" title="External financial-status record">
              This records your reviewed external finance/payroll reference in HR-EIS.
              It does not send money or execute an external financial transaction.
            </Alert>
            <TextInput label="Financial review evidence reference" required
              value={financialEvidence}
              onChange={(event) => setFinancialEvidence(event.currentTarget.value)} />
            <Checkbox label="External status is available" checked={externalStatusAvailable}
              onChange={(event) => setExternalStatusAvailable(event.currentTarget.checked)} />
            {!externalStatusAvailable && <Text size="sm">
              Record financial processing now. Leave external status unavailable until a verified report arrives.
            </Text>}
            {externalStatusAvailable && <>
            <Select label="External source system" required value={sourceSystem}
              data={[{ value: "finance", label: "Finance" },
                { value: "payroll", label: "Payroll" }]}
              onChange={(value) =>
                setSourceSystem(value === "payroll" ? "payroll" : "finance")} />
            <TextInput label="External status reference" required
              value={statusReference}
              onChange={(event) => setStatusReference(event.currentTarget.value)} />
            <Select label="Status reported by the external system" required
              value={paymentStatus}
              data={["processing", "payment_pending", "paid", "failed"]}
              onChange={(value) =>
                setPaymentStatus(
                  value === "processing" || value === "paid" || value === "failed"
                    ? value : "payment_pending"
                )} />
            </>}
          </>}
          {mode === "appraisal" && <Alert color="blue" title="Assigned appraisal action">
            {isFinalAuthority ? "Finalize and archive the reviewed appraisal."
              : "Forward the reviewed appraisal to the next assigned authority."}
          </Alert>}
          <Group justify="flex-end">
            <Button variant="default" disabled={pending}
              onClick={() => setMode(null)}>Cancel</Button>
            <Button loading={pending} onClick={submit}>
              {mode === "finance" ? externalStatusAvailable
                ? "Record external status" : "Record financial processing"
                : mode === "financial_review" ? "Record finance review" : "Record decision"}
            </Button>
          </Group>
        </Stack>
      </Drawer>
    </>
  );
}
