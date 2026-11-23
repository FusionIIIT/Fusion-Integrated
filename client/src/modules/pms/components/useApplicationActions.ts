// Which actions the acting role may take on one application, decided from permissions,
// status and the person's relation; the server re-checks every one.
import { useAuth } from "../../../auth/AuthProvider";
import * as h from "../api/hooks";
import type { ApplicationDetail } from "../api/types";
import { type Action, action, num, str } from "./ActionBar";
import type { FieldSpec, FieldValue } from "./FieldsModal";
import { words } from "./format";
import { usePmsCan } from "./access";

const EDITABLE = ["draft", "needs_revision", "rejected"];
const BUDGET_OK = ["approved", "pending_review", "attorney_assigned"];
const JUSTIFY: FieldSpec = { name: "justification", label: "Justification (at least 50 characters)",
  type: "textarea", required: true };

const opts = (values: string[]) => values.map((v) => ({ value: v, label: words(v) }));
const today = () => new Date().toISOString().slice(0, 10);

function useMutations() {
  return {
    update: h.useUpdateApplication(), submit: h.useSubmit(), resubmit: h.useResubmit(),
    appeal: h.useFileAppeal(), withdraw: h.useWithdraw(), approveOa: h.useApproveResponse(),
    review: h.useReviewDecision(), appealDecision: h.useAppealDecision(),
    budgetDecision: h.useBudgetDecision(), renewal: h.useRenewalDecision(),
    assignDirector: h.useAssignDirector(), assignAppeal: h.useAssignAppeal(),
    assignAttorney: h.useAssignAttorney(), routeBudget: h.useRouteBudget(),
    external: h.useExternalDecision(), reassignRenewal: h.useReassignRenewal(),
    respond: h.useRespondAssignment(), assess: h.useSaveAssessment(),
    finalize: h.useFinalizeAssessment(), legalRequest: h.useLegalRequest(),
    advice: h.useLegalAdvice(), propose: h.useProposeBudget(), filing: h.useRecordFiling(),
    communication: h.useRecordCommunication(), prepare: h.usePrepareResponse(),
    submission: h.useRecordSubmission(), extension: h.useRecordExtension(),
    addCycle: h.useAddCycle(), requestRenewal: h.useRequestRenewal(),
    maintenance: h.useRecordMaintenance(),
  };
}

type Mutations = ReturnType<typeof useMutations>;

export function useApplicationActions(app: ApplicationDetail | undefined): Action[] {
  const { session } = useAuth();
  const can = usePmsCan();
  const ref = h.useReferenceData();
  const panel = h.usePanelOptions();
  const isOffice = can("pms.review.assign");
  const directors = h.useDirectorCandidates(app && isOffice ? app.id : null);
  const attorneys = h.useAttorneyCandidates(app && can("pms.attorney.assign") ? app.id : null);
  const m = useMutations();
  if (!app || !session) return [];
  const me = session.user.id;
  const out: Action[] = [];
  const id = app.id;
  const latest = app.review_cycles[app.review_cycles.length - 1];
  const openCycle = app.review_cycles.find((c) => c.status === "open");
  const openAppeal = app.appeals.find((a) => a.status === "open");
  const live = app.attorney_assignments.find((a) => ["offered", "accepted"].includes(a.status));
  const myCase = live?.status === "accepted" && live.attorney_user_id === me;
  const openBudget = app.budgets.find((b) => ["proposed", "escalated", "escalation_tracked"]
    .includes(b.status));
  const approvedBudget = app.budgets.some((b) => ["approved", "external_approved"]
    .includes(b.status));
  const liveCycle = app.maintenance_cycles.find((c) => ["scheduled", "decision_requested",
    "renew_approved"].includes(c.status));

  // -- applicant -------------------------------------------------------------------
  if (app.applicant_user_id === me) {
    if (can("pms.application.update") && EDITABLE.includes(app.status)) {
      out.push(action({ key: "edit", label: "Edit details", title: "Edit the application",
        fields: [
          { name: "title", label: "Title", type: "text", required: true, initial: app.title },
          { name: "abstract", label: "Abstract", type: "textarea", initial: app.abstract },
          { name: "description", label: "Detailed description", type: "textarea",
            initial: app.description },
          { name: "claims", label: "Claims", type: "textarea", initial: app.claims },
          { name: "domain_code", label: "Technical area", type: "select",
            initial: app.domain_code || null,
            options: (ref.data?.domains ?? []).map((d) => ({ value: d.code, label: d.label })) },
          { name: "preferred_attorney_user_id", label: "Preferred attorney (optional)",
            type: "select", initial: app.preferred_attorney_user_id != null
              ? String(app.preferred_attorney_user_id) : null,
            options: (panel.data ?? []).map((p) => ({ value: String(p.user_id), label: p.name })) },
        ], submitLabel: "Save" }, m.update, (v) => ({ id, title: str(v.title),
        abstract: str(v.abstract), description: str(v.description), claims: str(v.claims),
        domain_code: str(v.domain_code), preferred_attorney_user_id:
          v.preferred_attorney_user_id ? num(v.preferred_attorney_user_id) : null })));
    }
    if (can("pms.application.create") && app.status === "draft") {
      out.push(action({ key: "submit", label: "Submit application", title: "Submit for review",
        subtitle: "You cannot edit the application while it is under review.", fields: [],
        submitLabel: "Submit" }, m.submit, () => id));
    }
    if (can("pms.application.update") && ["needs_revision", "rejected"].includes(app.status)) {
      const keys = Object.keys(app.feedback);
      out.push(action({ key: "resubmit", label: "Resubmit", title: "Resubmit the revision",
        subtitle: `Due by ${app.revision_due_on ?? "—"}. Answer each piece of feedback.`,
        fields: keys.map((k) => ({ name: `response_${k}`, required: true, type: "textarea",
          label: `How you addressed the ${k} feedback (at least 50 characters)`,
          description: app.feedback[k] })), submitLabel: "Resubmit" },
      m.resubmit, (v) => ({ id, responses: Object.fromEntries(keys.map((k) =>
        [k, str(v[`response_${k}`])])) })));
    }
    if (can("pms.appeal.create") && app.status === "rejected" && app.appeal_due_on) {
      out.push(action({ key: "appeal", label: "Appeal", title: "Appeal the rejection",
        subtitle: `Open until ${app.appeal_due_on}.`, fields: [
          { name: "grounds", label: "Grounds", type: "textarea", required: true },
          { name: "justification", label: "Justification", type: "textarea", required: true },
        ], submitLabel: "File appeal" }, m.appeal,
      (v) => ({ id, grounds: str(v.grounds), justification: str(v.justification) })));
    }
    if (can("pms.withdrawal.create") && ref.data?.withdrawal_statuses.includes(app.status)) {
      const co = app.inventors.filter((i) => i.user_id !== app.applicant_user_id);
      out.push(action({ key: "withdraw", label: "Withdraw", danger: true,
        title: "Withdraw the application", fields: [
          { name: "reason", label: "Reason", type: "textarea", required: true },
          ...(ref.data.withdrawal_consent_required && co.length ? [{
            name: "consent", label: "Co-inventors who consented", type: "multiselect" as const,
            required: true, options: co.map((i) => ({ value: String(i.id), label: i.name })) }]
            : []),
        ], submitLabel: "Withdraw" }, m.withdraw, (v) => ({ id, reason: str(v.reason),
        consented_inventor_ids: ((v.consent as string[] | null) ?? []).map(Number) })));
    }
    for (const oa of app.office_actions) {
      if (can("pms.office_action_response.approve")
          && oa.status === "awaiting_applicant_approval") {
        out.push(action({ key: `approve-oa-${oa.id}`, label: `Approve response ${oa.reference}`,
          title: "Approve the office-action response", subtitle: oa.draft_response.slice(0, 300),
          fields: [], submitLabel: "Approve" }, m.approveOa, () => oa.id));
      }
    }
  }

  // -- Director --------------------------------------------------------------------
  if (can("pms.review.approve") && openCycle?.director_user_id === me) {
    out.push(action({ key: "review", label: "Record decision", title: "Review decision",
      subtitle: `Due by ${openCycle.due_on}.`, fields: [
        { name: "decision", label: "Decision", type: "select", required: true,
          options: opts(["approve", "needs_revision", "reject"]) }, JUSTIFY,
      ], submitLabel: "Record decision" }, m.review,
    (v) => ({ id, decision: str(v.decision), justification: str(v.justification) })));
  }
  if (can("pms.appeal.review") && openAppeal?.director_user_id === me) {
    out.push(action({ key: "appeal-decision", label: "Decide appeal", title: "Appeal outcome",
      fields: [
        { name: "outcome", label: "Outcome", type: "select", required: true,
          options: [{ value: "uphold", label: "Uphold Rejection" },
            { value: "remand", label: "Remand for Amendment" },
            { value: "modify", label: "Modify Decision" }] },
        { name: "modified_decision", label: "New decision (when modifying)", type: "select",
          options: opts(["approve", "needs_revision"]) },
        { ...JUSTIFY, name: "note" },
      ], submitLabel: "Record outcome" }, m.appealDecision, (v) => ({ id: openAppeal.id,
      outcome: str(v.outcome), modified_decision: v.modified_decision ?? null, note: str(v.note) })));
  }
  if (can("pms.budget.approve") && openBudget?.status === "proposed"
      && latest?.director_user_id === me) {
    out.push(action({ key: "budget-decision", label: "Decide budget",
      title: `Budget of Rs ${openBudget.total}`,
      subtitle: "Above the configured threshold the decision is escalated automatically.",
      fields: [{ name: "decision", label: "Decision", type: "select", required: true,
        options: [{ value: "approve", label: "Approve" }, { value: "reject", label: "Reject" }] },
      { name: "note", label: "Note", type: "textarea" }], submitLabel: "Record" },
    m.budgetDecision, (v) => ({ id: openBudget.id, approve: v.decision === "approve",
      note: str(v.note) })));
  }
  for (const c of app.maintenance_cycles) {
    if (can("pms.renewal.approve") && c.status === "decision_requested"
        && c.deciding_director_user_id === me) {
      out.push(action({ key: `renewal-${c.id}`, label: "Decide renewal",
        title: `Renewal due ${c.due_on}`, fields: [{ name: "renew", label: "Decision",
          type: "select", required: true, options: [{ value: "yes", label: "Renew" },
            { value: "no", label: "Do Not Renew" }] },
        { name: "note", label: "Note", type: "textarea" }], submitLabel: "Record" },
      m.renewal, (v) => ({ id: c.id, renew: v.renew === "yes", note: str(v.note) })));
    }
  }

  // -- PCC_ADMIN -------------------------------------------------------------------
  // C10: an open review moves only once it is overdue or its Director has left the roster.
  const reviewer = openCycle?.director_user_id;
  const stuck = openCycle != null && (openCycle.due_on < today()
    || !(directors.data ?? []).some((c) => c.user_id === reviewer));
  if (isOffice && (["submitted", "resubmitted"].includes(app.status)
      || (app.status === "under_review" && stuck))) {
    const reassign = app.status === "under_review";
    out.push(action({ key: "assign-director", label: reassign ? "Reassign Director"
      : "Assign Director", title: reassign ? "Reassign the review" : "Assign a Director",
    subtitle: "Only unconflicted Directors listed for this area are offered, least busy first.",
    fields: [{ name: "director", label: "Director", type: "select", required: true,
      options: (directors.data ?? []).filter((c) => c.user_id !== reviewer)
        .map((c) => ({ value: String(c.user_id), label: `${c.name} — ${c.workload} open` })) }],
    submitLabel: "Assign" },
    m.assignDirector, (v) => ({ id, director_user_id: num(v.director) })));
  }
  if (isOffice && openAppeal) {
    const rejecter = app.review_cycles.find((c) => c.decision === "reject")?.director_user_id;
    out.push(action({ key: "assign-appeal", label: "Assign appeal Director",
      title: "Who hears the appeal", fields: [{ name: "director", label: "Director",
        type: "select", required: true, options: (directors.data ?? [])
          .filter((c) => c.user_id !== rejecter)
          .map((c) => ({ value: String(c.user_id), label: c.name })) }], submitLabel: "Assign" },
    m.assignAppeal, (v) => ({ id: openAppeal.id, director_user_id: num(v.director) })));
  }
  if (can("pms.attorney.assign") && ["approved", "pending_review"].includes(app.status) && !live) {
    out.push(action({ key: "assign-attorney", label: "Assign attorney", title: "Offer the case",
      fields: [
        { name: "attorney", label: "Panel attorney", type: "select",
          options: (attorneys.data ?? []).map((c) => ({ value: String(c.user_id),
            label: `${c.name} — ${c.workload} open` })) },
        { name: "other", label: "Or someone off the panel (needs an exception)", type: "person" },
        { name: "exception_reason", label: "Institutional exception", type: "textarea" },
      ], submitLabel: "Offer" }, m.assignAttorney, (v) => ({ id,
      attorney_user_id: num(v.attorney ?? v.other), exception_reason: str(v.exception_reason) })));
  }
  if (can("pms.escalation.review") && openBudget?.status === "escalated") {
    out.push(action({ key: "route-budget", label: "Route escalated budget",
      title: "Route to the higher authority", fields: [{ name: "routed_to",
        label: "Routed to", type: "text", required: true }], submitLabel: "Route" },
    m.routeBudget, (v) => ({ id: openBudget.id, routed_to: str(v.routed_to) })));
  }
  if (can("pms.escalation.review") && openBudget?.status === "escalation_tracked") {
    out.push(action({ key: "external", label: "Record authority's decision",
      title: "The higher authority's decision", fields: [
        { name: "approved", label: "Approved", type: "checkbox" },
        { name: "reference", label: "Decision reference", type: "text", required: true },
        { name: "decided_on", label: "Decided on", type: "date", required: true, initial: today() },
      ], submitLabel: "Record" }, m.external, (v) => ({ id: openBudget.id,
      approved: Boolean(v.approved), reference: str(v.reference), decided_on: str(v.decided_on) })));
  }
  for (const c of app.maintenance_cycles) {
    if (can("pms.renewal.assign") && c.status === "decision_requested") {
      out.push(action({ key: `reassign-renewal-${c.id}`, label: "Reassign renewal decision",
        title: "Give the decision to another Director", fields: [{ name: "director",
          label: "Director", type: "person", required: true, kind: "faculty" }],
        submitLabel: "Reassign" }, m.reassignRenewal,
      (v) => ({ id: c.id, director_user_id: num(v.director) })));
    }
  }

  // -- Attorney ---------------------------------------------------------------------
  if (can("pms.attorney_assignment.review") && live?.status === "offered"
      && live.attorney_user_id === me) {
    out.push(action({ key: "accept", label: "Accept case", title: "Accept the case",
      fields: [], submitLabel: "Accept" }, m.respond, () => ({ id: live.id, accept: true })));
    out.push(action({ key: "decline", label: "Decline case", danger: true,
      title: "Decline the case", fields: [{ name: "reason", label: "Reason", type: "textarea",
        required: true }], submitLabel: "Decline" }, m.respond,
    (v) => ({ id: live.id, accept: false, reason: str(v.reason) })));
  }
  if (myCase) addCaseWork(out, app, m, can, { openBudget: Boolean(openBudget), approvedBudget,
    liveCycle });
  return out;
}

function addCaseWork(out: Action[], app: ApplicationDetail, m: Mutations,
  can: (p: string) => boolean, state: { openBudget: boolean; approvedBudget: boolean;
    liveCycle: ApplicationDetail["maintenance_cycles"][number] | undefined }) {
  const id = app.id;
  const active = ["attorney_assigned", "filed", "granted"].includes(app.status);
  const draft = app.assessments.find((a) => a.status === "draft");
  if (can("pms.assessment.create") && active) {
    const fields: FieldSpec[] = ["analysis", "novelty", "non_obviousness", "utility"].map((k) => ({
      name: k, label: words(k), type: "textarea" as const,
      initial: (draft?.[k as keyof typeof draft] as FieldValue) ?? "" }));
    fields.push({ name: "recommendation", label: "Recommendation", type: "select",
      initial: draft?.recommendation || null,
      options: opts(["file_patent", "do_not_file", "needs_amendment"]) });
    out.push(action({ key: "assess", label: draft ? "Edit opinion draft" : "Record opinion",
      title: "Patentability assessment", fields, submitLabel: "Save draft" }, m.assess,
    (v) => ({ id, assessment_id: draft?.id ?? null, ...Object.fromEntries(
      fields.map((f) => [f.name, str(v[f.name])])) })));
    if (draft) {
      out.push(action({ key: "finalize", label: "Finalize opinion", title: "Finalize the opinion",
        subtitle: "A final opinion cannot be changed.", fields: [], submitLabel: "Finalize" },
      m.finalize, () => draft.id));
    }
  }
  if (can("pms.legal_request.create") && active) {
    out.push(action({ key: "legal-request", label: "Ask the applicant", title: "Request",
      fields: [{ name: "kind", label: "Kind", type: "select", required: true,
        options: opts(["information", "extension"]) },
      { name: "message", label: "Message", type: "textarea", required: true }],
      submitLabel: "Send" }, m.legalRequest,
    (v) => ({ id, kind: str(v.kind), message: str(v.message) })));
  }
  if (can("pms.legal_advice.create") && active) {
    out.push(action({ key: "advice", label: "Record advice", title: "Legal advice",
      fields: [{ name: "advice", label: "Advice", type: "textarea", required: true }],
      submitLabel: "Record" }, m.advice, (v) => ({ id, advice: str(v.advice) })));
  }
  if (can("pms.budget.create") && BUDGET_OK.includes(app.status) && !state.openBudget
      && !state.approvedBudget) {
    out.push(action({ key: "budget", label: "Propose budget", title: "Filing and prosecution budget",
      fields: [
        { name: "filing_fee", label: "Filing fees (Rs)", type: "text", required: true },
        { name: "attorney_fee", label: "Attorney fees (Rs)", type: "text", required: true },
        { name: "admin_cost", label: "Administrative costs (Rs)", type: "text", required: true },
      ], submitLabel: "Propose" }, m.propose, (v) => ({ id, filing_fee: str(v.filing_fee),
      attorney_fee: str(v.attorney_fee), admin_cost: str(v.admin_cost) })));
  }
  if (can("pms.filing.create") && ["attorney_assigned", "filed", "granted"].includes(app.status)) {
    out.push(action({ key: "filing", label: "Record filing", title: "External filing",
      subtitle: "Record it only once the patent office has confirmed the filing.", fields: [
        { name: "jurisdiction", label: "Jurisdiction code", type: "text", required: true,
          initial: "IN" },
        { name: "office_name", label: "Patent office", type: "text", required: true,
          initial: "Indian Patent Office" },
        { name: "external_filing_id", label: "Application number", type: "text", required: true },
        { name: "filing_date", label: "Filing date", type: "date", required: true, initial: today() },
        { name: "confirmation_reference", label: "Confirmation", type: "text", required: true },
        { name: "international_justification", label: "Justification (international filings)",
          type: "textarea" },
      ], submitLabel: "Record filing" }, m.filing, (v) => ({ id,
      jurisdiction: str(v.jurisdiction).toUpperCase(), office_name: str(v.office_name),
      external_filing_id: str(v.external_filing_id), filing_date: str(v.filing_date),
      confirmation_reference: str(v.confirmation_reference),
      international_justification: str(v.international_justification) })));
  }
  if (can("pms.communication.create") && ["filed", "granted"].includes(app.status)) {
    out.push(action({ key: "communication", label: "Record communication",
      title: "Patent-office communication", fields: [
        { name: "kind", label: "Kind", type: "select", required: true,
          options: opts(app.status === "filed" ? ["office_action", "grant", "refusal", "other"]
            : ["other"]) },
        { name: "received_on", label: "Received on", type: "date", required: true, initial: today() },
        { name: "reference", label: "Reference", type: "text", required: true },
        { name: "details", label: "Details", type: "textarea" },
        { name: "response_due_on", label: "Response due (office actions)", type: "date" },
        { name: "requires_applicant_review", label: "Applicant must approve the response",
          type: "checkbox" },
        { name: "grant_date", label: "Grant date (grants)", type: "date" },
        { name: "patent_number", label: "Patent number (grants)", type: "text" },
        { name: "jurisdiction", label: "Granted in (grants)", type: "text" },
      ], submitLabel: "Record" }, m.communication, (v) => ({ id, kind: str(v.kind),
      received_on: str(v.received_on), reference: str(v.reference), details: str(v.details),
      response_due_on: v.response_due_on || null, requires_applicant_review:
        Boolean(v.requires_applicant_review), grant_date: v.grant_date || null,
      patent_number: str(v.patent_number), jurisdiction: str(v.jurisdiction).toUpperCase() })));
  }
  for (const oa of app.office_actions) {
    if (can("pms.office_action_response.create") && oa.status === "recorded") {
      out.push(action({ key: `prepare-${oa.id}`, label: `Draft response ${oa.reference}`,
        title: "Office-action response", fields: [{ name: "draft", label: "Response",
          type: "textarea", required: true }], submitLabel: "Save response" }, m.prepare,
      (v) => ({ id: oa.id, draft: str(v.draft) })));
    }
    if (can("pms.office_action_response.update")
        && ["applicant_approved", "response_ready"].includes(oa.status)) {
      out.push(action({ key: `submit-${oa.id}`, label: `Record submission ${oa.reference}`,
        title: "Response submitted", subtitle: `Due by ${oa.current_due_on ?? "—"}.`, fields: [
          { name: "submitted_on", label: "Submitted on", type: "date", required: true,
            initial: today() },
          { name: "reference", label: "Submission reference", type: "text", required: true },
        ], submitLabel: "Record" }, m.submission, (v) => ({ id: oa.id,
        submitted_on: str(v.submitted_on), reference: str(v.reference) })));
    }
    if (can("pms.office_action_response.update") && oa.status !== "submitted") {
      out.push(action({ key: `extend-${oa.id}`, label: `Record extension ${oa.reference}`,
        title: "Extension granted", fields: [
          { name: "new_due_on", label: "New due date", type: "date", required: true },
          { name: "reason", label: "Reason", type: "textarea", required: true },
        ], submitLabel: "Record" }, m.extension, (v) => ({ id: oa.id,
        new_due_on: str(v.new_due_on), reason: str(v.reason) })));
    }
  }
  const cycle = state.liveCycle;
  if (can("pms.maintenance.update") && app.status === "granted" && !cycle) {
    out.push(action({ key: "add-cycle", label: "Add maintenance due date",
      title: "Maintenance due date", fields: [{ name: "due_on", label: "Due on", type: "date",
        required: true }], submitLabel: "Add" }, m.addCycle,
    (v) => ({ id, due_on: str(v.due_on) })));
  }
  if (can("pms.maintenance.update") && cycle?.status === "scheduled") {
    out.push(action({ key: "request-renewal", label: "Ask for renewal decision",
      title: `Renewal due ${cycle.due_on}`, fields: [], submitLabel: "Ask the Director" },
    m.requestRenewal, () => cycle.id));
  }
  if (can("pms.maintenance.update") && cycle?.status === "renew_approved") {
    out.push(action({ key: "record-maintenance", label: "Record maintenance payment",
      title: "Maintenance action", fields: [
        { name: "reference", label: "Receipt reference", type: "text", required: true },
        { name: "amount", label: "Amount (Rs)", type: "text", required: true },
        { name: "actioned_on", label: "Paid on", type: "date", required: true, initial: today() },
      ], submitLabel: "Record" }, m.maintenance, (v) => ({ id: cycle.id,
      reference: str(v.reference), amount: str(v.amount), actioned_on: str(v.actioned_on) })));
  }
}
