
import { Badge, Card, Container, Stack, Text } from "@mantine/core";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { usePmsAppeals, usePmsApplication } from "../api/hooks";
import { PmsActionForm } from "../components/PmsActionForm";
import { PmsApplicationSelect } from "../components/PmsApplicationSelect";

export default function ReviewsPage() {
  const { can } = useAuth();
  const [selected, setSelected] = useState<string | null>(null);
  const detail = usePmsApplication(selected ? Number(selected) : undefined);
  const appeals = usePmsAppeals();

  return (
    <Container size="xl">
      <PageHeader
        title="Reviews and decisions"
        subtitle="Submit Director decisions, review budgets, and follow appeal work."
      />

      <Card padding="lg">
        <PmsApplicationSelect
          value={selected}
          onChange={setSelected}
        />
      </Card>

      {detail.error && (
        <Card mt="md">
          <ErrorState error={detail.error} />
        </Card>
      )}

      {detail.isPending && selected && (
        <Text c="dimmed" mt="md">
          Loading application…
        </Text>
      )}

      {detail.data && (
        <Stack mt="md" gap="md">
          <Card padding="md">
            <PageHeader
              title={`${detail.data.application_no} · ${detail.data.title}`}
              subtitle={detail.data.domain}
              action={<StatusBadge status={detail.data.status} />}
            />

            {detail.data.director_reviews.map((review) => (
              <Text key={review.id} size="sm" c="dimmed">
                {review.decision} · Director {review.director_user_id} ·{" "}
                {review.decided_at}
              </Text>
            ))}
          </Card>

          {can("pms.application.review") &&
            detail.data.status === "under_review" && (
              <PmsActionForm
                title="Technical review decision"
                path={() => `/applications/${detail.data!.id}/review/`}
                fields={[
                  {
                    name: "decision",
                    label: "Decision",
                    type: "select",
                    required: true,
                    options: [
                      { value: "Approve", label: "Approve" },
                      { value: "Reject", label: "Reject" },
                      {
                        value: "Needs Revision",
                        label: "Needs Revision",
                      },
                    ],
                  },
                  {
                    name: "justification",
                    label: "Justification (at least 50 characters)",
                    type: "textarea",
                    required: true,
                  },
                  {
                    name: "feedback",
                    label: "Feedback for Applicant",
                    type: "textarea",
                  },
                ]}
                successTitle="Review recorded"
                successMessage="PMS recorded the Director decision and audit history."
                submitLabel="Record decision"
              />
            )}

          {can("pms.budget.review") &&
            detail.data.status === "approved" && (
              <>
                <PmsActionForm
                  method="put"
                  title="Budget line items"
                  path={() => `/applications/${detail.data!.id}/budget/`}
                  fields={[
                    {
                      name: "filing_fees",
                      label: "Filing fees",
                      type: "number",
                      required: true,
                    },
                    {
                      name: "attorney_fees",
                      label: "Attorney fees",
                      type: "number",
                      required: true,
                    },
                    {
                      name: "administrative_costs",
                      label: "Administrative costs",
                      type: "number",
                      required: true,
                    },
                    {
                      name: "threshold_limit",
                      label: "Threshold limit (optional)",
                      type: "number",
                    },
                  ]}
                  transform={(body) =>
                    Object.fromEntries(
                      Object.entries(body).filter(
                        ([, value]) => value !== "",
                      ),
                    )
                  }
                  successTitle="Budget submitted"
                  successMessage="PMS stored the proposed budget for review."
                />

                {detail.data.budget && (
                  <Card withBorder padding="md">
                    <PageHeader
                      title="Current budget"
                      action={
                        <StatusBadge status={detail.data.budget.status} />
                      }
                    />
                    <Text size="sm">
                      Total cost: {detail.data.budget.total_cost}
                    </Text>
                  </Card>
                )}

                <PmsActionForm
                  title="Budget decision"
                  path={() => `/applications/${detail.data!.id}/budget/`}
                  fields={[
                    {
                      name: "decision",
                      label: "Decision",
                      type: "select",
                      required: true,
                      options: [
                        { value: "Approve", label: "Approve" },
                        { value: "Reject", label: "Reject" },
                        { value: "Escalate", label: "Escalate" },
                      ],
                    },
                    {
                      name: "justification",
                      label: "Justification",
                      type: "textarea",
                    },
                  ]}
                  transform={(body) =>
                    Object.fromEntries(
                      Object.entries(body).filter(
                        ([, value]) => value !== "",
                      ),
                    )
                  }
                  successTitle="Budget decision recorded"
                  successMessage="PMS recorded the decision or escalation outcome."
                />
              </>
            )}
        </Stack>
      )}

      {can("pms.application.review_appeal") && (
        <Card padding="md" mt="md">
          <PageHeader
            title="Appeal review queue"
            subtitle="Review appeals submitted against patent application decisions."
          />

          {appeals.isPending && (
            <Text c="dimmed">Loading appeals...</Text>
          )}

          {appeals.error && (
            <ErrorState error={appeals.error} />
          )}

          {appeals.data?.length === 0 && !appeals.isPending && (
            <Text c="dimmed">
              No appeals are currently available for review.
            </Text>
          )}

          {appeals.data?.map((appeal) => (
            <Card key={appeal.id} withBorder padding="md" mt="sm">
              <Stack gap="xs">
                <PageHeader
                  title={`${appeal.application_no} · ${appeal.application_title}`}
                  subtitle={`Appeal #${appeal.id} · Applicant ${appeal.applicant_user_id}`}
                  action={<Badge>{appeal.status}</Badge>}
                />

                <Text size="sm">
                  <strong>Grounds:</strong> {appeal.grounds}
                </Text>

                <Text size="sm">
                  <strong>Justification:</strong> {appeal.justification}
                </Text>

                {appeal.status === "submitted" && (
                  <PmsActionForm
                    title="Appeal decision"
                    path={() => `/appeals/${appeal.id}/review/`}
                    fields={[
                      {
                        name: "outcome",
                        label: "Decision",
                        type: "select",
                        required: true,
                        options: [
                            { value: "Remand for Amendment", label: "Remand for Amendment" },
                            { value: "Uphold Rejection", label: "Uphold Rejection" },
                            { value: "Modify Decision", label: "Modify Decision" },
                        ]
                      },
                      {
                        name: "outcome_justification",
                        label: "Decision justification",
                        type: "textarea",
                        required: true,
                      },
                    ]}
                    successTitle="Appeal decision recorded"
                    successMessage="The appeal decision has been saved."
                    submitLabel="Submit decision"
                  />
                )}
              </Stack>
            </Card>
          ))}
        </Card>
      )}
    </Container>
  );
}
