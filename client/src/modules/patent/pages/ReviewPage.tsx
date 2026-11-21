import { useState } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Stack, Text,
  TextInput, Select, NumberInput, Textarea, Modal,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle, FaTimesCircle, FaExclamationTriangle } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { usePendingApplications, useAdminApplications } from "../api/hooks";
import type { Application } from "../api/types";

// --- Types for Modals ---

interface ApprovalDecision {
  approved: boolean;
  justification?: string;
}

interface BudgetDecision {
  approved: boolean;
  proposed_budget?: number | null;
  justification?: string;
}

interface AppealDecision {
  upheld: boolean;
  justification?: string;
}

// --- Components ---

function ApprovalModal({
  application,
  isOpen,
  onClose,
  onApprove,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (decision: ApprovalDecision) => void;
}) {
  const [approved, setApproved] = useState(true);
  const [justification, setJustification] = useState("");

  const handleSubmit = () => {
    if (!justification.trim()) {
      notifications.show({
        message: "Justification is required.",
        color: "red",
      });
      return;
    }
    onApprove({ approved, justification: justification.trim() });
    setApproved(true);
    setJustification("");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Decision for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Application Status: {application.status}</Text>
        <Text order={3}>{application.abstract}</Text>

        <Group orientation="horizontal" gap="xs">
          <LabelWithCheckbox label="Approve Application">
            <input
              type="checkbox"
              checked={approved}
              onChange={(e) => setApproved(e.target.checked)}
            />
          </LabelWithCheckbox>
          <LabelWithCheckbox label="Reject Application">
            <input
              type="checkbox"
              checked={!approved}
              onChange={(e) => setApproved(!e.target.checked)}
            />
          </LabelWithCheckbox>
        </Group>

        {(!approved || !justification) && (
          <Text size="sm" c="dimmed">
            Select an option above to proceed.
          </Text>
        )}

        <Textarea
          label="Justification (required if rejecting)"
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Explain the reason for your decision..."
          required={!approved}
          minRows={4}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Submit Decision
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function BudgetModal({
  application,
  isOpen,
  onClose,
  onApprove,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onApprove: (decision: BudgetDecision) => void;
}) {
  const [approved, setApproved] = useState(true);
  const [proposedBudget, setProposedBudget] = useState<number | null>(null);
  const [justification, setJustification] = useState("");

  const handleSubmit = () => {
    if (!justification.trim()) {
      notifications.show({
        message: "Justification is required.",
        color: "red",
      });
      return;
    }
    onApprove({ approved, proposed_budget: proposedBudget, justification: justification.trim() });
    setApproved(true);
    setProposedBudget(null);
    setJustification("");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Budget Decision for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Current Budget: {application.budget_total ?? "Not set"}</Text>

        <Group orientation="horizontal" gap="xs">
          <LabelWithCheckbox label="Approve Proposed Budget">
            <input
              type="checkbox"
              checked={approved}
              onChange={(e) => setApproved(e.target.checked)}
            />
          </LabelWithCheckbox>
          <LabelWithCheckbox label="Reject Proposed Budget">
            <input
              type="checkbox"
              checked={!approved}
              onChange={(e) => setApproved(!e.target.checked)}
            />
          </LabelWithCheckbox>
        </Group>

        {(!approved || !proposedBudget) && (
          <Text size="sm" c="dimmed">
            Select an option above to proceed.
          </Text>
        )}

        <NumberInput
          label="Proposed Budget Amount ($)"
          value={proposedBudget ?? 0}
          onChange={(v) => setProposedBudget(v)}
          step={100}
          precision={0}
        />

        <Textarea
          label="Justification (required if rejecting)"
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Explain the reason for your decision..."
          required={!approved}
          minRows={4}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Submit Decision
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function AppealModal({
  application,
  isOpen,
  onClose,
  onDecide,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onDecide: (decision: AppealDecision) => void;
}) {
  const [upheld, setUpheld] = useState(true);
  const [justification, setJustification] = useState("");

  const handleSubmit = () => {
    if (!justification.trim()) {
      notifications.show({
        message: "Justification is required.",
        color: "red",
      });
      return;
    }
    onDecide({ upheld, justification: justification.trim() });
    setUpheld(true);
    setJustification("");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Appeal Decision for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Current Status: {application.status}</Text>

        <Group orientation="horizontal" gap="xs">
          <LabelWithCheckbox label="Uphold Original Decision">
            <input
              type="checkbox"
              checked={upheld}
              onChange={(e) => setUpheld(e.target.checked)}
            />
          </LabelWithCheckbox>
          <LabelWithCheckbox label="Overturn Original Decision">
            <input
              type="checkbox"
              checked={!upheld}
              onChange={(e) => setUpheld(!e.target.checked)}
            />
          </LabelWithCheckbox>
        </Group>

        {(!upheld || !justification) && (
          <Text size="sm" c="dimmed">
            Select an option above to proceed.
          </Text>
        )}

        <Textarea
          label="Justification (required if overturning)"
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Explain the reason for your decision..."
          required={!upheld}
          minRows={4}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Submit Decision
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

export default function ReviewPage() {
  const { data: pendingApps, isPending: pendingLoading } = usePendingApplications();
  const { data: adminApps, isPending: adminLoading } = useAdminApplications();

  // Combine lists for the table (Director sees pending + assigned)
  const allApps = [...(pendingApps?.results ?? []), ...(adminApps?.results ?? [])];

  const [approvalModalId, setApprovalModalId] = useState<number | null>(null);
  const [budgetModalId, setBudgetModalId] = useState<number | null>(null);
  const [appealModalId, setAppealModalId] = useState<number | null>(null);

  // Handlers for Approval
  const handleApprovalSubmit = async (id: number, decision: ApprovalDecision) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await updatePatentApplication(id, { status: ... })
      notifications.show({
        title: "Decision Submitted",
        message: `Application ${decision.approved ? "approved" : "rejected"} successfully.`,
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

  // Handlers for Budget
  const handleBudgetSubmit = async (id: number, decision: BudgetDecision) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await decideBudget(id, ...)
      notifications.show({
        title: "Budget Decision Submitted",
        message: `Budget ${decision.approved ? "approved" : "rejected"} successfully.`,
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

  // Handlers for Appeal
  const handleAppealSubmit = async (id: number, decision: AppealDecision) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await decideAppeal(id, ...)
      notifications.show({
        title: "Appeal Decision Submitted",
        message: `Appeal ${decision.upheld ? "upheld" : "overturned"} successfully.`,
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

  if (pendingLoading || adminLoading) {
    return (
      <Container size="xl">
        <PageHeader title="Director Review" subtitle="Review pending and assigned applications" />
        <Card padding="lg">
          <DataTable<Application>
            rows={allApps}
            loading={pendingLoading || adminLoading}
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
                    {r.status === "under_review" && (
                      <>
                        <Button
                          size="xs" variant="default" color="blue"
                          onClick={() => setApprovalModalId(r.id)}
                        >
                          Approve/Reject
                        </Button>
                        <Button
                          size="xs" variant="default" color="orange"
                          onClick={() => setBudgetModalId(r.id)}
                        >
                          Budget Decision
                        </Button>
                      </>
                    )}
                    {r.status === "shortlisted" && (
                      <Button
                        size="xs" variant="default" color="purple"
                        onClick={() => setAppealModalId(r.id)}
                      >
                        Review Appeal
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
      <PageHeader title="Director Review" subtitle="Review pending and assigned applications" />
      <Card padding="lg">
        <DataTable<Application>
          rows={allApps}
          loading={pendingLoading || adminLoading}
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
                  {r.status === "under_review" && (
                    <>
                      <Button
                        size="xs" variant="default" color="blue"
                        onClick={() => setApprovalModalId(r.id)}
                      >
                        Approve/Reject
                      </Button>
                      <Button
                        size="xs" variant="default" color="orange"
                        onClick={() => setBudgetModalId(r.id)}
                      >
                        Budget Decision
                      </Button>
                    </>
                  )}
                  {r.status === "shortlisted" && (
                    <Button
                      size="xs" variant="default" color="purple"
                      onClick={() => setAppealModalId(r.id)}
                    >
                      Review Appeal
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <ApprovalModal
        application={allApps.find((a) => a.id === approvalModalId)!}
        isOpen={!!approvalModalId}
        onClose={() => setApprovalModalId(null)}
        onApprove={(decision) => handleApprovalSubmit(approvalModalId!, decision)}
      />

      <BudgetModal
        application={allApps.find((a) => a.id === budgetModalId)!}
        isOpen={!!budgetModalId}
        onClose={() => setBudgetModalId(null)}
        onApprove={(decision) => handleBudgetSubmit(budgetModalId!, decision)}
      />

      <AppealModal
        application={allApps.find((a) => a.id === appealModalId)!}
        isOpen={!!appealModalId}
        onClose={() => setAppealModalId(null)}
        onDecide={(decision) => handleAppealSubmit(appealModalId!, decision)}
      />
    </Container>
  );
}
