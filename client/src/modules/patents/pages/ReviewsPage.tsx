import { useState } from "react";
import { Alert, Button, Container, Group, Table, Text } from "@mantine/core";
import { FaClipboardCheck, FaInfoCircle } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications } from "../api/hooks";
import type { PatentApplicationSummary } from "../api/types";
import { PatentStatusBadge } from "../components/PatentStatusBadge";
import { ReviewDecisionModal } from "../components/ReviewDecisionModal";

export default function ReviewsPage() {
  const { data, isPending, error } = useApplications();
  const [reviewTarget, setReviewTarget] = useState<PatentApplicationSummary | null>(null);

  if (error) {
    return (
      <Container size="lg">
        <ErrorState error={error} />
      </Container>
    );
  }

  if (isPending) {
    return (
      <Container size="lg">
        <Text c="dimmed">Loading…</Text>
      </Container>
    );
  }

  const applications = (data?.results ?? []).filter((app) =>
    ["SUBMITTED", "DIRECTOR_ASSIGNED", "UNDER_REVIEW", "RESUBMITTED", "APPEAL_SUBMITTED"].includes(app.status),
  );

  return (
    <Container size="lg">
      <PageHeader
        title="Director Review Queue"
        subtitle="Evaluate invention disclosures for technical merit and patentability"
      />

      {applications.length === 0 ? (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="Review queue empty">
          <Text size="sm">There are no patent applications currently awaiting director evaluation.</Text>
        </Alert>
      ) : (
        <Table withTableBorder withColumnBorders striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Application No</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {applications.map((app) => (
              <Table.Tr key={app.id}>
                <Table.Td>{app.application_number || `PMS-${app.id}`}</Table.Td>
                <Table.Td fw={500}>{app.title}</Table.Td>
                <Table.Td>{app.domain_category}</Table.Td>
                <Table.Td>
                  <PatentStatusBadge status={app.status} />
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      leftSection={<FaClipboardCheck size={12} />}
                      aria-label={`Evaluate ${app.title}`}
                      onClick={() => setReviewTarget(app)}
                    >
                      Evaluate
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {reviewTarget && (
        <ReviewDecisionModal
          opened={Boolean(reviewTarget)}
          onClose={() => setReviewTarget(null)}
          applicationId={reviewTarget.id}
          applicationTitle={reviewTarget.title}
        />
      )}
    </Container>
  );
}
