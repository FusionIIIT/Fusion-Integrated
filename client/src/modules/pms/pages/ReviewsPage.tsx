import { Alert, Card, Container, Stack, Text } from "@mantine/core";
import { FaInfoCircle } from "react-icons/fa";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { usePmsApplication } from "../api/hooks";
import { PmsActionForm } from "../components/PmsActionForm";
import { PmsApplicationSelect } from "../components/PmsApplicationSelect";

export default function ReviewsPage() {
  const { can } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = usePmsApplication(selected ? Number(selected) : undefined);

  return (
    <Container size="xl">
      <PageHeader title="Reviews and decisions" subtitle="Submit Director decisions, review budgets, and follow appeal work." />
      <Card padding="lg">
        <PmsApplicationSelect value={selected} onChange={setSelected} />
      </Card>
      {detail.error && <Card mt="md"><ErrorState error={detail.error} /></Card>}
      {detail.isPending && selected && <Text c="dimmed" mt="md">Loading application…</Text>}
      {detail.data && (
        <Stack mt="md" gap="md">
          <Card padding="md">
            <PageHeader title={`${detail.data.application_no} · ${detail.data.title}`}
              subtitle={detail.data.domain} action={<StatusBadge status={detail.data.status} />} />
            {detail.data.director_reviews.map((review) => (
              <Text key={review.id} size="sm" c="dimmed">
                {review.decision} · Director {review.director_user_id} · {review.decided_at}
              </Text>
            ))}
          </Card>

          {can("pms.application.review") && detail.data.status === "under_review" && (
            <PmsActionForm
              title="Technical review decision"
              path={() => `/applications/${detail.data!.id}/review/`}
              fields={[
                { name: "decision", label: "Decision", type: "select", required: true, options: [
                  { value: "Approve", label: "Approve" },
                  { value: "Reject", label: "Reject" },
                  { value: "Needs Revision", label: "Needs Revision" },
                ] },
                { name: "justification", label: "Justification (at least 50 characters)", type: "textarea", required: true },
                { name: "feedback", label: "Feedback for Applicant", type: "textarea" },
              ]}
              successTitle="Review recorded"
              successMessage="PMS recorded the Director decision and audit history."
              submitLabel="Record decision"
            />
          )}

          {can("pms.budget.review") && detail.data.status === "approved" && (
            <>
              <PmsActionForm
                method="put"
                title="Budget line items"
                path={() => `/applications/${detail.data!.id}/budget/`}
                fields={[
                  { name: "filing_fees", label: "Filing fees", type: "number", required: true },
                  { name: "attorney_fees", label: "Attorney fees", type: "number", required: true },
                  { name: "administrative_costs", label: "Administrative costs", type: "number", required: true },
                  { name: "threshold_limit", label: "Threshold limit (optional)", type: "number" },
                ]}
                transform={(body) => Object.fromEntries(
                  Object.entries(body).filter(([, value]) => value !== ""),
                )}
                successTitle="Budget submitted"
                successMessage="PMS stored the proposed budget for review."
              />
              {detail.data.budget && (
                <Card withBorder padding="md">
                  <PageHeader title="Current budget" action={<StatusBadge status={detail.data.budget.status} />} />
                  <Text size="sm">Total cost: {detail.data.budget.total_cost}</Text>
                </Card>
              )}
              <PmsActionForm
                title="Budget decision"
                path={() => `/applications/${detail.data!.id}/budget/`}
                fields={[
                  { name: "decision", label: "Decision", type: "select", required: true, options: [
                    { value: "Approve", label: "Approve" },
                    { value: "Reject", label: "Reject" },
                    { value: "Escalate", label: "Escalate" },
                  ] },
                  { name: "justification", label: "Justification", type: "textarea" },
                ]}
                transform={(body) => Object.fromEntries(
                  Object.entries(body).filter(([, value]) => value !== ""),
                )}
                successTitle="Budget decision recorded"
                successMessage="PMS recorded the decision or escalation outcome."
              />
            </>
          )}

          {can("pms.application.review_appeal") && (
            <Alert color="blue" variant="light" icon={<FaInfoCircle />} title="Appeal review queue unavailable">
              PMS exposes a decision endpoint for a known appeal ID, but no API lists appeals or includes appeal IDs in application details. The review queue cannot be completed without that backend capability.
            </Alert>
          )}
        </Stack>
      )}
    </Container>
  );
}
