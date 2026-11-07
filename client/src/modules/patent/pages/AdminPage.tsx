import { useState } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Stack, Text,
  TextInput, Select, NumberInput, Modal,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUserPlus, FaMoneyBillWave } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAdminApplications } from "../api/hooks";
import type { Application } from "../api/types";

// --- Types for Modals ---

interface AssignDirectorData {
  director_id: number;
}

interface AssignAttorneyData {
  attorney_assigned: boolean;
}

interface ProposeBudgetData {
  proposed_budget: number | null;
}

// --- Components ---

function AssignDirectorModal({
  application,
  isOpen,
  onClose,
  onAssign,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onAssign: (data: AssignDirectorData) => void;
}) {
  const [directorId, setDirectorId] = useState<string>("");

  const handleSubmit = () => {
    if (!directorId.trim()) {
      notifications.show({
        message: "Director ID is required.",
        color: "red",
      });
      return;
    }
    onAssign({ director_id: parseInt(directorId, 10) });
    setDirectorId("");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Assign Director for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Select the PCC Director to assign this application to.</Text>

        <TextInput
          label="Director ID"
          value={directorId}
          onChange={(e) => setDirectorId(e.target.value)}
          placeholder="e.g., 101"
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Assign Director
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function AssignAttorneyModal({
  application,
  isOpen,
  onClose,
  onAssign,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onAssign: (data: AssignAttorneyData) => void;
}) {
  const [attorneyAssigned, setAttorneyAssigned] = useState(false);

  const handleSubmit = () => {
    onAssign({ attorney_assigned: attorneyAssigned });
    setAttorneyAssigned(!attorneyAssigned);
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Assign Attorney for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Toggle attorney assignment status.</Text>

        <Group orientation="horizontal" gap="xs">
          <LabelWithCheckbox label="Assign Attorney">
            <input
              type="checkbox"
              checked={attorneyAssigned}
              onChange={(e) => setAttorneyAssigned(e.target.checked)}
            />
          </LabelWithCheckbox>
        </Group>

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Update Assignment
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function ProposeBudgetModal({
  application,
  isOpen,
  onClose,
  onPropose,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onPropose: (data: ProposeBudgetData) => void;
}) {
  const [proposedBudget, setProposedBudget] = useState<number | null>(null);

  const handleSubmit = () => {
    onPropose({ proposed_budget: proposedBudget });
    setProposedBudget(null);
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Propose Budget for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Propose a budget amount (or null to clear).</Text>

        <NumberInput
          label="Proposed Budget Amount ($)"
          value={proposedBudget ?? 0}
          onChange={(v) => setProposedBudget(v)}
          step={100}
          precision={0}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Propose Budget
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function LabelWithCheckbox({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <LabelWithCheckboxWrapper>
      <span>{label}</span>
      {children}
    </LabelWithCheckboxWrapper>
  );
}

const LabelWithCheckboxWrapper = ({ children }: { children: React.ReactNode }) => (
  <Group orientation="horizontal" gap="xs">
    {children}
  </Group>
);

// --- Main Component ---

export default function AdminPage() {
  const { data, isPending } = useAdminApplications();

  // Combine lists for the table (Admin sees all submitted)
  const allApps = (data?.results ?? []) as Application[];

  const [assignDirectorModalId, setAssignDirectorModalId] = useState<number | null>(null);
  const [assignAttorneyModalId, setAssignAttorneyModalId] = useState<number | null>(null);
  const [proposeBudgetModalId, setProposeBudgetModalId] = useState<number | null>(null);

  // Handlers for Assign Director
  const handleDirectorSubmit = async (id: number, data: AssignDirectorData) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await updatePatentApplication(id, { assigned_director_id })
      notifications.show({
        title: "Director Assigned",
        message: `Application assigned to Director ${data.director_id}.`,
        color: "success",
      });
    } catch (e) {
      notifications.show({
        title: "Error",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  // Handlers for Assign Attorney
  const handleAttorneySubmit = async (id: number, data: AssignAttorneyData) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await updatePatentApplication(id, { attorney_assigned })
      notifications.show({
        title: "Attorney Assignment Updated",
        message: `Attorney assignment set to ${data.attorney_assigned ? "Yes" : "No"}.`,
        color: "success",
      });
    } catch (e) {
      notifications.show({
        title: "Error",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  // Handlers for Propose Budget
  const handleBudgetSubmit = async (id: number, data: ProposeBudgetData) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await proposeBudget(id, ...)
      notifications.show({
        title: "Budget Proposed",
        message: `Budget proposal submitted for $${data.proposed_budget ?? 0}.`,
        color: "success",
      });
    } catch (e) {
      notifications.show({
        title: "Error",
        message: errorMessage(e),
        color: "red",
      });
    }
  };

  if (isPending) {
    return (
      <Container size="xl">
        <PageHeader title="PCC Admin" subtitle="Manage all submitted applications" />
        <Card padding="lg">
          <DataTable<Application>
            rows={allApps}
            loading={isPending}
            rowKey={(r) => r.id}
            minWidth={900}
            columns={[
              {
                key: "title", header: "Application",
                render: (r) => <Text fw={600}>{r.title}</Text>,
              },
              {
                key: "status", header: "Status",
                render: (r) => <StatusBadge status={r.status} />,
              },
              {
                key: "actions", header: "", align: "right",
                render: (r) => (
                  <Group justify="flex-end" gap="xs">
                    {!r.assigned_director_id && (
                      <Button
                        size="xs" variant="default" color="green"
                        onClick={() => setAssignDirectorModalId(r.id)}
                      >
                        Assign Director
                      </Button>
                    )}
                    {r.attorney_assigned === false && (
                      <Button
                        size="xs" variant="default" color="purple"
                        onClick={() => setAssignAttorneyModalId(r.id)}
                      >
                        Assign Attorney
                      </Button>
                    )}
                    {!r.budget_total && (
                      <Button
                        size="xs" variant="default" color="orange"
                        onClick={() => setProposeBudgetModalId(r.id)}
                      >
                        Propose Budget
                      </Button>
                    )}
                  </Group>
                ),
              },
            ]}
          />
        </Card>
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader title="PCC Admin" subtitle="Manage all submitted applications" />
      <Card padding="lg">
        <DataTable<Application>
          rows={allApps}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={900}
          columns={[
            {
              key: "title", header: "Application",
              render: (r) => <Text fw={600}>{r.title}</Text>,
            },
            {
              key: "status", header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "actions", header: "", align: "right",
              render: (r) => (
                <Group justify="flex-end" gap="xs">
                  {!r.assigned_director_id && (
                    <Button
                      size="xs" variant="default" color="green"
                      onClick={() => setAssignDirectorModalId(r.id)}
                    >
                      Assign Director
                    </Button>
                  )}
                  {r.attorney_assigned === false && (
                    <Button
                      size="xs" variant="default" color="purple"
                      onClick={() => setAssignAttorneyModalId(r.id)}
                    >
                      Assign Attorney
                    </Button>
                  )}
                  {!r.budget_total && (
                    <Button
                      size="xs" variant="default" color="orange"
                      onClick={() => setProposeBudgetModalId(r.id)}
                    >
                      Propose Budget
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <AssignDirectorModal
        application={allApps.find((a) => a.id === assignDirectorModalId)!}
        isOpen={!!assignDirectorModalId}
        onClose={() => setAssignDirectorModalId(null)}
        onAssign={(data) => handleDirectorSubmit(assignDirectorModalId!, data)}
      />

      <AssignAttorneyModal
        application={allApps.find((a) => a.id === assignAttorneyModalId)!}
        isOpen={!!assignAttorneyModalId}
        onClose={() => setAssignAttorneyModalId(null)}
        onAssign={(data) => handleAttorneySubmit(assignAttorneyModalId!, data)}
      />

      <ProposeBudgetModal
        application={allApps.find((a) => a.id === proposeBudgetModalId)!}
        isOpen={!!proposeBudgetModalId}
        onClose={() => setProposeBudgetModalId(null)}
        onPropose={(data) => handleBudgetSubmit(proposeBudgetModalId!, data)}
      />
    </Container>
  );
}
