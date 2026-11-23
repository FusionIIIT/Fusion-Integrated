import { useState, type FormEvent } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { usePatientRecords, useReimbursementClaims, useSubmitClaim,
  useTransitionClaim } from "../api/hooks";
import type { ReimbursementClaim } from "../api/types";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";

function claimAction(claim: ReimbursementClaim, can: (permission: string) => boolean,
  run: (id: number, event: "review" | "verification" | "sanction" | "payment",
    decision?: "approve" | "reject") => void) {
  if (claim.state === "pending_phc_review" && can("phc.reimbursement.review")) {
    return <button type="button" onClick={() => run(claim.id, "review")}>Forward to Accounts</button>;
  }
  if (claim.state === "pending_accounts_verification" && can("phc.reimbursement.manage")) {
    return <button type="button" onClick={() => run(claim.id, "verification")}>Verify claim</button>;
  }
  if (claim.state === "pending_sanction" && can("phc.reimbursement.approve")) {
    return <>
      <button type="button" onClick={() => run(claim.id, "sanction", "approve")}>Approve sanction</button>
      <button type="button" onClick={() => run(claim.id, "sanction", "reject")}>Reject claim</button>
    </>;
  }
  if (claim.state === "approved_for_payment" && can("phc.reimbursement.manage")) {
    return <button type="button" onClick={() => run(claim.id, "payment")}>Record payment</button>;
  }
  return null;
}

export default function ReimbursementsPage() {
  const { can } = useAuth();
  const claims = useReimbursementClaims();
  const records = usePatientRecords();
  const submit = useSubmitClaim();
  const review = useTransitionClaim("review");
  const verification = useTransitionClaim("verification");
  const sanction = useTransitionClaim("sanction");
  const payment = useTransitionClaim("payment");
  const [prescriptionId, setPrescriptionId] = useState("");
  const [amount, setAmount] = useState("");
  const [expenseDate, setExpenseDate] = useState("");
  const [billReference, setBillReference] = useState("");
  const [remarks, setRemarks] = useState("");
  const saving = submit.isPending || review.isPending || verification.isPending ||
    sanction.isPending || payment.isPending;

  function submitClaim(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submit.mutate({ prescription_id: Number(prescriptionId), claim_amount: amount,
      expense_date: expenseDate, bill_reference: billReference, remarks });
  }

  function run(id: number, event: "review" | "verification" | "sanction" | "payment",
    decision?: "approve" | "reject") {
    const mutation = { review, verification, sanction, payment }[event];
    mutation.mutate({ id, decision });
  }

  const ownPrescriptions = records.data?.results.flatMap((visit) => visit.prescriptions) ?? [];
  return <ResourcePanel title="Reimbursement claims" data={claims.data}
    isPending={claims.isPending || (can("phc.reimbursement.create") && records.isPending)}
    isError={claims.isError || (can("phc.reimbursement.create") && records.isError)}
    error={claims.error ?? records.error} emptyText="No reimbursement claims are available."
    renderRow={(claim) => <article>
      <h2>Claim {claim.id}</h2>
      <p>{claim.state.replaceAll("_", " ")} — {claim.claim_amount} — expense date {claim.expense_date}</p>
      <ol aria-label={`Claim ${claim.id} history`}>
        {claim.actions.map((action, index) => <li key={`${action.created_at}-${index}`}>
          {action.event}: {action.from_state} → {action.to_state}
        </li>)}
      </ol>
      {claimAction(claim, can, run)}
    </article>}>
    {can("phc.reimbursement.create") && <form onSubmit={submitClaim}>
      <h2>Submit a reimbursement claim</h2>
      <label htmlFor="claim-prescription">Prescription</label>
      <select id="claim-prescription" required value={prescriptionId}
        onChange={(event) => setPrescriptionId(event.target.value)}>
        <option value="">Choose a prescription</option>
        {ownPrescriptions.map((prescription) => <option key={prescription.id} value={prescription.id}>
          {prescription.issued_on} — {prescription.details}
        </option>)}
      </select>
      <label htmlFor="claim-amount">Claim amount</label>
      <input id="claim-amount" type="number" min="0.01" step="0.01" required
        value={amount} onChange={(event) => setAmount(event.target.value)} />
      <label htmlFor="claim-expense-date">Expense date</label>
      <input id="claim-expense-date" type="date" required value={expenseDate}
        onChange={(event) => setExpenseDate(event.target.value)} />
      <label htmlFor="claim-bill-reference">Bill reference (optional)</label>
      <input id="claim-bill-reference" value={billReference}
        onChange={(event) => setBillReference(event.target.value)} />
      <label htmlFor="claim-remarks">Remarks (optional)</label>
      <textarea id="claim-remarks" value={remarks}
        onChange={(event) => setRemarks(event.target.value)} />
      <button type="submit" disabled={saving || !ownPrescriptions.length}>Submit claim</button>
      <MutationMessage isPending={submit.isPending} isError={submit.isError}
        error={submit.error} isSuccess={submit.isSuccess} />
      {records.data && ownPrescriptions.length === 0 &&
        <p>A recorded prescription is required before you can submit a claim.</p>}
    </form>}
    {[review, verification, sanction, payment].some((mutation) => mutation.isError) &&
      <p role="alert">{[review, verification, sanction, payment].find((mutation) => mutation.isError)?.error instanceof Error
        ? ([review, verification, sanction, payment].find((mutation) => mutation.isError)?.error as Error).message
        : "The claim could not be updated."}</p>}
  </ResourcePanel>;
}
