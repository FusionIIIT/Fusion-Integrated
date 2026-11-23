import { Container } from "@mantine/core";
import { FaHandshake } from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAddNote, useApplications, useLicensing, useRecordLicense, useRouteLicensing,
  useSubmitLicensing,
} from "../api/hooks";
import type { LicensingRequest } from "../api/types";
import { type Action, ActionBar, action, num, str } from "../components/ActionBar";
import { words } from "../components/format";
import { usePmsCan } from "../components/access";

const today = () => new Date().toISOString().slice(0, 10);

// UC-PMS-020, 021: requests, their routing, negotiation and the final agreement.
export default function LicensingPage() {
  const can = usePmsCan();
  const list = useLicensing();
  const submit = useSubmitLicensing();
  const route = useRouteLicensing();
  const note = useAddNote();
  const agreement = useRecordLicense();
  const mine = useApplications();
  const choices = (mine.data?.results ?? []).filter((a) => a.status !== "draft")
    .map((a) => ({ value: String(a.id), label: `${a.reference} — ${a.title}` }));
  const create = can("pms.licensing_request.create") ? [action({ key: "new",
    label: "New request", title: "Licensing or technology transfer", fields: [
      { name: "application_id", label: "Application", type: "select", required: true,
        options: choices },
      { name: "kind", label: "Kind", type: "select", required: true, options: [
        { value: "licensing", label: "Licensing" },
        { value: "technology_transfer", label: "Technology transfer" }] },
      { name: "summary", label: "What you want to license or transfer", type: "textarea",
        required: true },
    ], submitLabel: "Submit" }, submit, (v) => ({ application_id: num(v.application_id),
    kind: str(v.kind), summary: str(v.summary) }))] : [];

  const rowActions = (r: LicensingRequest): Action[] => {
    if (!can("pms.licensing_request.review")) return [];
    const out: Action[] = [];
    if (r.status === "submitted") {
      out.push(action({ key: `route-${r.id}`, label: "Route", title: "Route the request",
        fields: [], submitLabel: "Route" }, route, () => r.id));
    }
    if (["routed", "negotiating"].includes(r.status)) {
      out.push(action({ key: `note-${r.id}`, label: "Add note", title: "Negotiation note",
        fields: [{ name: "note", label: "Note", type: "textarea", required: true }],
        submitLabel: "Add" }, note, (v) => ({ id: r.id, note: str(v.note) })));
    }
    if (r.status === "negotiating") {
      out.push(action({ key: `agree-${r.id}`, label: "Record agreement",
        title: "Final agreement", fields: [
          { name: "counterparty", label: "Other party", type: "text", required: true },
          { name: "signed_on", label: "Signed on", type: "date", required: true, initial: today() },
          { name: "terms_summary", label: "Terms", type: "textarea", required: true },
          { name: "financial_terms", label: "Financial terms", type: "textarea" },
        ], submitLabel: "Record" }, agreement, (v) => ({ id: r.id,
        counterparty: str(v.counterparty), signed_on: str(v.signed_on),
        terms_summary: str(v.terms_summary), financial_terms: str(v.financial_terms) })));
    }
    return out;
  };

  return (
    <Container size="xl" pt="md">
      <PageHeader title="Licensing" subtitle="Licensing and technology-transfer requests"
        action={<ActionBar actions={create} />} />
      {list.error ? <ErrorState error={list.error} /> : (
        <DataTable<LicensingRequest>
          rows={list.data ?? []} loading={list.isPending} rowKey={(r) => r.id}
          empty={{ icon: FaHandshake, title: "No licensing requests" }}
          columns={[
            { key: "application_reference", header: "Application" },
            { key: "kind", header: "Kind", render: (r) => words(r.kind) },
            { key: "summary", header: "Summary" },
            { key: "route", header: "Routed to", render: (r) => r.committee_name
              || (r.routed_director_user_id ? "A Director" : "Not routed") },
            { key: "status", header: "Status", render: (r) => <StatusBadge status={r.status} /> },
            { key: "act", header: "", align: "right",
              render: (r) => <ActionBar actions={rowActions(r)} /> },
          ]}
        />
      )}
    </Container>
  );
}
