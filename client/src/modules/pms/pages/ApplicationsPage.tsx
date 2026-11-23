import { Container } from "@mantine/core";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateApplication, useReferenceData } from "../api/hooks";
import { ActionBar, action, str } from "../components/ActionBar";
import { ApplicationsTable, WorkQueue } from "../components/Lists";
import { usePmsCan } from "../components/access";

// UC-PMS-001, 002: the applicant's own applications and what waits on them.
export default function ApplicationsPage() {
  const can = usePmsCan();
  const create = useCreateApplication();
  const ref = useReferenceData();
  const actions = can("pms.application.create") ? [action({
    key: "new", label: "New application", title: "Start a patent application",
    subtitle: "Save a draft now; add inventors and documents before you submit.",
    fields: [
      { name: "title", label: "Title", type: "text", required: true },
      { name: "abstract", label: "Abstract", type: "textarea" },
      { name: "domain_code", label: "Technical area", type: "select",
        options: (ref.data?.domains ?? []).map((d) => ({ value: d.code, label: d.label })) },
    ], submitLabel: "Save draft" }, create, (v) => ({ title: str(v.title),
    abstract: str(v.abstract), domain_code: str(v.domain_code) }))] : [];
  return (
    <Container size="xl" pt="md">
      <PageHeader title="My Applications" subtitle="Patent applications you made or are named on"
        action={<ActionBar actions={actions} />} />
      <WorkQueue kinds={["draft", "revision", "office_action_approval"]}
        emptyTitle="Nothing is waiting on you" />
      <ApplicationsTable emptyTitle="No applications yet"
        emptyDescription="Start one with New application." />
    </Container>
  );
}
