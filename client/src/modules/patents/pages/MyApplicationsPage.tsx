import { useState } from "react";
import { Alert, Button, Container, Group, Table, Text } from "@mantine/core";
import { FaInfoCircle, FaPlus } from "react-icons/fa";
import { Link } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications } from "../api/hooks";
import type { PatentApplicationSummary } from "../api/types";
import { AppealModal } from "../components/AppealModal";
import { PatentStatusBadge } from "../components/PatentStatusBadge";
import { WithdrawModal } from "../components/WithdrawModal";

export default function MyApplicationsPage() {
  const { data, isPending, error } = useApplications();
  const { can } = useAuth();

  const [withdrawTarget, setWithdrawTarget] = useState<PatentApplicationSummary | null>(null);
  const [appealTarget, setAppealTarget] = useState<PatentApplicationSummary | null>(null);

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

  const applications = data?.results ?? [];

  return (
    <Container size="lg">
      <PageHeader
        title="My Applications"
        subtitle="Manage and track your patent applications and filings"
        action={
          can("patents.application.create") ? (
            <Button
              component={Link}
              to="/patents/new"
              leftSection={<FaPlus size={12} />}
              aria-label="New Application"
            >
              New Application
            </Button>
          ) : undefined
        }
      />

      {applications.length === 0 ? (
        <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="No applications found">
          <Text size="sm">
            You haven&apos;t submitted any patent applications yet. Click &quot;New Application&quot; to begin.
          </Text>
        </Alert>
      ) : (
        <Table withTableBorder withColumnBorders striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Application No</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Jurisdiction</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {applications.map((app) => (
              <Table.Tr key={app.id}>
                <Table.Td>{app.application_number || `PMS-${app.id}`}</Table.Td>
                <Table.Td fw={500}>{app.title}</Table.Td>
                <Table.Td>
                  <PatentStatusBadge status={app.status} />
                </Table.Td>
                <Table.Td>{app.jurisdiction}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {can("patents.application.withdraw") &&
                      ["DRAFT", "SUBMITTED", "DIRECTOR_ASSIGNED", "UNDER_REVIEW", "NEEDS_REVISION", "APPROVED"].includes(
                        app.status,
                      ) && (
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          aria-label={`Withdraw ${app.title}`}
                          onClick={() => setWithdrawTarget(app)}
                        >
                          Withdraw
                        </Button>
                      )}
                    {can("patents.application.appeal") && app.status === "REJECTED" && (
                      <Button
                        size="xs"
                        color="violet"
                        variant="light"
                        aria-label={`Appeal ${app.title}`}
                        onClick={() => setAppealTarget(app)}
                      >
                        Appeal
                      </Button>
                    )}
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {withdrawTarget && (
        <WithdrawModal
          opened={Boolean(withdrawTarget)}
          onClose={() => setWithdrawTarget(null)}
          applicationId={withdrawTarget.id}
          applicationTitle={withdrawTarget.title}
        />
      )}

      {appealTarget && (
        <AppealModal
          opened={Boolean(appealTarget)}
          onClose={() => setAppealTarget(null)}
          applicationId={appealTarget.id}
          applicationTitle={appealTarget.title}
        />
      )}
    </Container>
  );
}
