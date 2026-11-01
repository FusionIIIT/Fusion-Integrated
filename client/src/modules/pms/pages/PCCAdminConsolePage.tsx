import { useState } from "react";
import {
  ActionIcon,
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaAward,
  FaCoins,
  FaHistory,
  FaUserCheck,
  FaUserTie,
} from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { type Column, DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useApplications,
  useAssignDirector,
  useGrantPatent,
} from "../api/hooks";
import type { PatentApplicationListItem } from "../api/types";
import { AttorneyAssignModal } from "../components/AttorneyAssignModal";
import { BudgetApprovalModal } from "../components/BudgetApprovalModal";
import { HistoryDrawer } from "../components/HistoryDrawer";
import { StatusBadge } from "../components/StatusBadge";

export default function PCCAdminConsolePage() {
  const [assignDirectorAppId, setAssignDirectorAppId] = useState<number | null>(null);
  const [directorId, setDirectorId] = useState<string>("9001");
  const [dueDays, setDueDays] = useState<number | string>(14);

  const [assignAttorneyAppId, setAssignAttorneyAppId] = useState<number | null>(null);
  const [budgetAppId, setBudgetAppId] = useState<number | null>(null);
  const [historyAppId, setHistoryAppId] = useState<number | null>(null);

  const { data, isPending, error } = useApplications();
  const assignDirectorMutation = useAssignDirector(assignDirectorAppId ?? 0);
  const grantMutation = useGrantPatent(0);

  const handleAssignDirector = async () => {
    if (!assignDirectorAppId || !directorId) return;

    try {
      await assignDirectorMutation.mutateAsync({
        director_user_id: Number(directorId),
        due_days: Number(dueDays) || 14,
      });
      notifications.show({
        color: "green",
        message: "Director assigned for review (BR-PMS-010).",
      });
      setAssignDirectorAppId(null);
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const handleGrantPatent = async (appId: number) => {
    const grantNo = prompt(`Enter official Patent Grant Number for App #${appId} (e.g. IN-459012):`);
    if (!grantNo) return;

    try {
      await grantMutation.mutateAsync({
        grant_number: grantNo.trim(),
        grant_date: new Date().toISOString().split("T")[0] || "",
      });
      notifications.show({
        color: "green",
        message: `Patent ${grantNo} granted! 20-year maintenance schedules created.`,
      });
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  const columns: Column<PatentApplicationListItem>[] = [
    {
      key: "application_no",
      header: "Application No.",
      render: (row) => (
        <Text fw={600} size="sm">
          {row.application_no}
        </Text>
      ),
    },
    {
      key: "title",
      header: "Title",
      render: (row) => (
        <Stack gap={2}>
          <Text fw={500} size="sm">
            {row.title}
          </Text>
          <Text size="xs" c="dimmed">
            Domain: {row.domain} | Lead: {row.primary_inventor_name || "N/A"}
          </Text>
        </Stack>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row) => <StatusBadge status={row.status} />,
    },
    {
      key: "actions",
      header: "",
      render: (row) => (
        <Group justify="flex-end" gap="xs">
          {row.status === "submitted" && (
            <Button
              size="xs"
              color="indigo"
              leftSection={<FaUserCheck />}
              onClick={() => setAssignDirectorAppId(row.id)}
            >
              Assign Director
            </Button>
          )}

          {["approved", "budget_approved"].includes(row.status) && (
            <Button
              size="xs"
              color="teal"
              leftSection={<FaUserTie />}
              onClick={() => setAssignAttorneyAppId(row.id)}
            >
              Assign Attorney
            </Button>
          )}

          {["approved", "attorney_assigned"].includes(row.status) && !row.has_budget && (
            <Button
              size="xs"
              color="lime"
              variant="light"
              leftSection={<FaCoins />}
              onClick={() => setBudgetAppId(row.id)}
            >
              Set Budget
            </Button>
          )}

          {["filed", "response_submitted"].includes(row.status) && (
            <Button
              size="xs"
              color="green"
              leftSection={<FaAward />}
              onClick={() => handleGrantPatent(row.id)}
            >
              Grant Patent
            </Button>
          )}

          <ActionIcon
            variant="subtle"
            color="gray"
            title="Audit History"
            onClick={() => setHistoryAppId(row.id)}
          >
            <FaHistory />
          </ActionIcon>
        </Group>
      ),
    },
  ];

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Patent Cell Coordination (PCC) Console"
        subtitle="Central administrative triage, Director assignment, attorney empanelment coordination, and budget authorization."
      />

      {error && <ErrorState error={error} />}

      <Card withBorder p={0}>
        <DataTable
          columns={columns}
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(row) => row.id}
          empty={{
            title: "No applications to coordinate",
            description: "No patent disclosures currently requiring PCC attention.",
          }}
        />
      </Card>

      {/* Assign Director Modal */}
      <FormModal
        opened={assignDirectorAppId != null}
        onClose={() => setAssignDirectorAppId(null)}
        title="Assign Reviewing Director"
        onSubmit={handleAssignDirector}
        submitLabel="Confirm Assignment"
        submitting={assignDirectorMutation.isPending}
      >
        <Stack gap="md">
          <Select
            label="Reviewing Director"
            value={directorId}
            onChange={(val) => setDirectorId(val ?? "9001")}
            data={[
              { value: "9001", label: "Dr. A. Sharma (Director - Engineering)" },
              { value: "9002", label: "Dr. R. Verma (Director - Sciences)" },
              { value: "9003", label: "Prof. S. Iyer (Dean - R&D)" },
            ]}
            required
          />

          <NumberInput
            label="Review Due Window (Days / BR-PMS-010)"
            value={dueDays}
            onChange={setDueDays}
            min={1}
            max={60}
            required
          />
        </Stack>
      </FormModal>

      {/* Assign Attorney Modal */}
      <AttorneyAssignModal
        applicationId={assignAttorneyAppId}
        opened={assignAttorneyAppId != null}
        onClose={() => setAssignAttorneyAppId(null)}
      />

      {/* Budget Modal */}
      <BudgetApprovalModal
        applicationId={budgetAppId}
        opened={budgetAppId != null}
        onClose={() => setBudgetAppId(null)}
      />

      {/* History Drawer */}
      <HistoryDrawer
        applicationId={historyAppId}
        onClose={() => setHistoryAppId(null)}
      />
    </Container>
  );
}
