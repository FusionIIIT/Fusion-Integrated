import { useState } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Stack, Text,
  TextInput, Select, NumberInput, Modal,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaFileAlt, FaBriefcase, FaPenFancy } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useMyApplications, usePendingApplications } from "../api/hooks";
import type { Application } from "../api/types";

// --- Types for Modals ---

interface AssignmentOfferData {
  offer_id: number;
  status: "accepted" | "declined";
}

interface OpinionData {
  opinion_text: string;
}

interface FilingData {
  filing_number: string;
  filing_date: string;
  jurisdiction: string;
}

interface OfficeActionData {
  action_number: string;
  received_date: string;
  description: string;
}

interface GrantDecisionData {
  granted: boolean;
  grant_type: "utility" | "design" | "plant";
  issue_fee: number;
  justification?: string;
}

// --- Components ---

function AssignmentModal({
  application,
  isOpen,
  onClose,
  onAccept,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onAccept: (data: AssignmentOfferData) => void;
}) {
  const [offerId, setOfferId] = useState<string>("");
  const [status, setStatus] = useState<"accepted" | "declined">("accepted");

  const handleSubmit = () => {
    if (!offerId.trim()) {
      notifications.show({
        message: "Offer ID is required.",
        color: "red",
      });
      return;
    }
    onAccept({ offer_id: parseInt(offerId, 10), status });
    setOfferId("");
    setStatus("accepted");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Assignment Offer for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Select an offer ID and your decision.</Text>

        <TextInput
          label="Offer ID"
          value={offerId}
          onChange={(e) => setOfferId(e.target.value)}
          placeholder="e.g., 5001"
        />

        <Group orientation="horizontal" gap="xs">
          <LabelWithCheckbox label="Accept Offer">
            <input
              type="radio"
              name="assignment_status"
              value="accepted"
              checked={status === "accepted"}
              onChange={(e) => setStatus(e.target.value as "accepted" | "declined")}
            />
          </LabelWithCheckbox>
          <LabelWithCheckbox label="Decline Offer">
            <input
              type="radio"
              name="assignment_status"
              value="declined"
              checked={status === "declined"}
              onChange={(e) => setStatus(e.target.value as "accepted" | "declined")}
            />
          </LabelWithCheckbox>
        </Group>

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Submit Decision
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function OpinionModal({
  application,
  isOpen,
  onClose,
  onRecord,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onRecord: (data: OpinionData) => void;
}) {
  const [opinionText, setOpinionText] = useState("");

  const handleSubmit = () => {
    if (!opinionText.trim()) {
      notifications.show({
        message: "Opinion text is required.",
        color: "red",
      });
      return;
    }
    onRecord({ opinion_text: opinionText.trim() });
    setOpinionText("");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Record Attorney Opinion for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Enter your professional opinion regarding this application.</Text>

        <Textarea
          label="Opinion Text"
          value={opinionText}
          onChange={(e) => setOpinionText(e.target.value)}
          placeholder="Provide detailed feedback..."
          minRows={5}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Record Opinion
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function FilingModal({
  application,
  isOpen,
  onClose,
  onRecord,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onRecord: (data: FilingData) => void;
}) {
  const [filingNumber, setFilingNumber] = useState("");
  const [filingDate, setFilingDate] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");

  const handleSubmit = () => {
    if (!filingNumber.trim() || !filingDate.trim() || !jurisdiction.trim()) {
      notifications.show({
        message: "All fields are required.",
        color: "red",
      });
      return;
    }
    onRecord({
      filing_number: filingNumber.trim(),
      filing_date: filingDate.trim(),
      jurisdiction: jurisdiction.trim(),
    });
    setFilingNumber("");
    setFilingDate("");
    setJurisdiction("");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Record External Filing for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Enter details of the external patent office filing.</Text>

        <TextInput
          label="Filing Number"
          value={filingNumber}
          onChange={(e) => setFilingNumber(e.target.value)}
          placeholder="e.g., US123456789"
        />

        <TextInput
          label="Filing Date (ISO)"
          type="date"
          value={filingDate}
          onChange={(e) => setFilingDate(e.target.value)}
        />

        <TextInput
          label="Jurisdiction"
          value={jurisdiction}
          onChange={(e) => setJurisdiction(e.target.value)}
          placeholder="e.g., USPTO, EPO"
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Record Filing
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function OfficeActionModal({
  application,
  isOpen,
  onClose,
  onRecord,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onRecord: (data: OfficeActionData) => void;
}) {
  const [actionNumber, setActionNumber] = useState("");
  const [receivedDate, setReceivedDate] = useState("");
  const [description, setDescription] = useState("");

  const handleSubmit = () => {
    if (!actionNumber.trim() || !receivedDate.trim() || !description.trim()) {
      notifications.show({
        message: "All fields are required.",
        color: "red",
      });
      return;
    }
    onRecord({
      action_number: actionNumber.trim(),
      received_date: receivedDate.trim(),
      description: description.trim(),
    });
    setActionNumber("");
    setReceivedDate("");
    setDescription("");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Record Office Action for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Enter details of the office action received.</Text>

        <TextInput
          label="Action Number"
          value={actionNumber}
          onChange={(e) => setActionNumber(e.target.value)}
          placeholder="e.g., 2023-123456"
        />

        <TextInput
          label="Received Date (ISO)"
          type="date"
          value={receivedDate}
          onChange={(e) => setReceivedDate(e.target.value)}
        />

        <Textarea
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe the examiner's objections..."
          minRows={4}
        />

        <Group justify="flex-end" gap="sm">
          <Button variant="default" onClick={handleSubmit}>
            Record Action
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function GrantDecisionModal({
  application,
  isOpen,
  onClose,
  onDecide,
}: {
  application: Application;
  isOpen: boolean;
  onClose: () => void;
  onDecide: (data: GrantDecisionData) => void;
}) {
  const [granted, setGranted] = useState(true);
  const [grantType, setGrantType] = useState<"utility" | "design" | "plant">("utility");
  const [issueFee, setIssueFee] = useState<number>(0);
  const [justification, setJustification] = useState("");

  const handleSubmit = () => {
    if (!justification.trim()) {
      notifications.show({
        message: "Justification is required.",
        color: "red",
      });
      return;
    }
    onDecide({ granted, grant_type: grantType, issue_fee: issueFee, justification: justification.trim() });
    setGranted(true);
    setGrantType("utility");
    setIssueFee(0);
    setJustification("");
    onClose();
  };

  return (
    <Modal
      opened={isOpen}
      title={`Grant Decision for ${application.title}`}
      size="lg"
      closeOnClickOutside
      withCloseButton
    >
      <Stack gap="md">
        <Text order={2}>Make a final decision on the grant.</Text>

        <Group orientation="horizontal" gap="xs">
          <LabelWithCheckbox label="Grant Patent">
            <input
              type="checkbox"
              checked={granted}
              onChange={(e) => setGranted(e.target.checked)}
            />
          </LabelWithCheckbox>
        </Group>

        <Select
          label="Patent Type"
          value={grantType}
          onChange={(v) => setGrantType(v as "utility" | "design" | "plant")}
        >
          <option value="utility">Utility</option>
          <option value="design">Design</option>
          <option value="plant">Plant</option>
        </Select>

        <NumberInput
          label="Issue Fee ($)"
          value={issueFee}
          onChange={(v) => setIssueFee(v)}
          step={100}
          precision={0}
        />

        <Textarea
          label="Justification (required)"
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Explain the reasoning for your decision..."
          minRows={4}
          required={!granted}
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

export default function AttorneyPage() {
  const { data: myApps, isPending: myLoading } = useMyApplications();
  const { data: pendingApps, isPending: pendingLoading } = usePendingApplications();

  // Combine lists for the table (Attorney sees assigned + pending review)
  const allApps = [...(myApps?.results ?? []), ...(pendingApps?.results ?? [])];

  const [assignmentModalId, setAssignmentModalId] = useState<number | null>(null);
  const [opinionModalId, setOpinionModalId] = useState<number | null>(null);
  const [filingModalId, setFilingModalId] = useState<number | null>(null);
  const [officeActionModalId, setOfficeActionModalId] = useState<number | null>(null);
  const [grantDecisionModalId, setGrantDecisionModalId] = useState<number | null>(null);

  // Handlers for Assignment Offer
  const handleAssignmentSubmit = async (id: number, data: AssignmentOfferData) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await updatePatentApplication(id, { attorney_assigned })
      notifications.show({
        title: "Assignment Submitted",
        message: `Offer ${data.status === "accepted" ? "accepted" : "declined"} successfully.`,
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

  // Handlers for Opinion
  const handleOpinionSubmit = async (id: number, data: OpinionData) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await recordOpinion(...)
      notifications.show({
        title: "Opinion Recorded",
        message: `Attorney opinion recorded successfully.`,
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

  // Handlers for Filing
  const handleFilingSubmit = async (id: number, data: FilingData) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await recordFiling(...)
      notifications.show({
        title: "Filing Recorded",
        message: `External filing recorded successfully.`,
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

  // Handlers for Office Action
  const handleOfficeActionSubmit = async (id: number, data: OfficeActionData) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await recordOfficeAction(...)
      notifications.show({
        title: "Office Action Recorded",
        message: `Office action recorded successfully.`,
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

  // Handlers for Grant Decision
  const handleGrantSubmit = async (id: number, data: GrantDecisionData) => {
    try {
      // Simulate API call structure based on api.ts patterns
      // In real implementation: await recordGrant(...)
      notifications.show({
        title: "Grant Decision Recorded",
        message: `Grant decision recorded successfully.`,
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

  if (myLoading || pendingLoading) {
    return (
      <Container size="xl">
        <PageHeader title="Attorney Dashboard" subtitle="Manage assignments, filings, and grants" />
        <Card padding="lg">
          <DataTable<Application>
            rows={allApps}
            loading={myLoading || pendingLoading}
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
                    {r.attorney_assigned === false && (
                      <Button
                        size="xs" variant="default" color="blue"
                        onClick={() => setAssignmentModalId(r.id)}
                      >
                        Assign Offer
                      </Button>
                    )}
                    {r.status === "under_review" && (
                      <Button
                        size="xs" variant="default" color="purple"
                        onClick={() => setOpinionModalId(r.id)}
                      >
                        Record Opinion
                      </Button>
                    )}
                    {r.status === "shortlisted" && (
                      <>
                        <Button
                          size="xs" variant="default" color="green"
                          onClick={() => setFilingModalId(r.id)}
                        >
                          Record Filing
                        </Button>
                        <Button
                          size="xs" variant="default" color="orange"
                          onClick={() => setOfficeActionModalId(r.id)}
                        >
                          Office Action
                        </Button>
                      </>
                    )}
                    {r.status === "selected" && (
                      <Button
                        size="xs" variant="default" color="red"
                        onClick={() => setGrantDecisionModalId(r.id)}
                      >
                        Grant Decision
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
      <PageHeader title="Attorney Dashboard" subtitle="Manage assignments, filings, and grants" />
      <Card padding="lg">
        <DataTable<Application>
          rows={allApps}
          loading={myLoading || pendingLoading}
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
                  {r.attorney_assigned === false && (
                    <Button
                      size="xs" variant="default" color="blue"
                      onClick={() => setAssignmentModalId(r.id)}
                    >
                      Assign Offer
                    </Button>
                  )}
                  {r.status === "under_review" && (
                    <Button
                      size="xs" variant="default" color="purple"
                      onClick={() => setOpinionModalId(r.id)}
                    >
                      Record Opinion
                    </Button>
                  )}
                  {r.status === "shortlisted" && (
                    <>
                      <Button
                        size="xs" variant="default" color="green"
                        onClick={() => setFilingModalId(r.id)}
                      >
                        Record Filing
                      </Button>
                      <Button
                        size="xs" variant="default" color="orange"
                        onClick={() => setOfficeActionModalId(r.id)}
                      >
                        Office Action
                      </Button>
                    </>
                  )}
                  {r.status === "selected" && (
                    <Button
                      size="xs" variant="default" color="red"
                      onClick={() => setGrantDecisionModalId(r.id)}
                    >
                      Grant Decision
                    </Button>
                  )}
                </Group>
              ),
            },
          ]}
        />
      </Card>

      <AssignmentModal
        application={allApps.find((a) => a.id === assignmentModalId)!}
        isOpen={!!assignmentModalId}
        onClose={() => setAssignmentModalId(null)}
        onAccept={(data) => handleAssignmentSubmit(assignmentModalId!, data)}
      />

      <OpinionModal
        application={allApps.find((a) => a.id === opinionModalId)!}
        isOpen={!!opinionModalId}
        onClose={() => setOpinionModalId(null)}
        onRecord={(data) => handleOpinionSubmit(opinionModalId!, data)}
      />

      <FilingModal
        application={allApps.find((a) => a.id === filingModalId)!}
        isOpen={!!filingModalId}
        onClose={() => setFilingModalId(null)}
        onRecord={(data) => handleFilingSubmit(filingModalId!, data)}
      />

      <OfficeActionModal
        application={allApps.find((a) => a.id === officeActionModalId)!}
        isOpen={!!officeActionModalId}
        onClose={() => setOfficeActionModalId(null)}
        onRecord={(data) => handleOfficeActionSubmit(officeActionModalId!, data)}
      />

      <GrantDecisionModal
        application={allApps.find((a) => a.id === grantDecisionModalId)!}
        isOpen={!!grantDecisionModalId}
        onClose={() => setGrantDecisionModalId(null)}
        onDecide={(data) => handleGrantSubmit(grantDecisionModalId!, data)}
      />
    </Container>
  );
}
