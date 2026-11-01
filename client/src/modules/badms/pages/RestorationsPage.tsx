import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import {
  FaCheck,
  FaCheckCircle,
  FaExclamationCircle,
  FaPlus,
  FaShieldAlt,
  FaTimes,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useRestorationDecision,
  useRestorations,
  useSubmitRestoration,
} from "../api";
import type { RestorationRequest } from "../api";

function getRestorationStatusBadge(status: string) {
  switch (status) {
    case "completed":
      return <Badge color="green">Restored & Verified</Badge>;
    case "pending_approval":
      return <Badge color="yellow">Awaiting SysAdmin Approval</Badge>;
    case "rejected":
      return <Badge color="red">Rejected</Badge>;
    case "failed":
      return <Badge color="dark">Failed</Badge>;
    default:
      return <Badge color="blue">{status}</Badge>;
  }
}

export default function RestorationsPage() {
  const { data: restorationsData, isLoading } = useRestorations();
  const submitRestoration = useSubmitRestoration();
  const decideRestoration = useRestorationDecision();

  const [requestModalOpen, setRequestModalOpen] = useState(false);
  const [targetType, setTargetType] = useState<"archive" | "backup">("archive");
  const [targetId, setTargetId] = useState<number | string>(1);
  const [reason, setReason] = useState("");
  const [destination, setDestination] = useState("/restored");
  const [feedbackMsg, setFeedbackMsg] = useState<{ text: string; error?: boolean } | null>(null);

  // Reject modal state
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [selectedRequest, setSelectedRequest] = useState<RestorationRequest | null>(null);
  const [rejectComments, setRejectComments] = useState("");

  const restorations = restorationsData?.results || [];
  const pendingApprovals = restorations.filter(
    (r) => r.is_sensitive && r.status === "pending_approval",
  );

  const handleSubmit = async () => {
    setFeedbackMsg(null);
    const numId = typeof targetId === "number" ? targetId : parseInt(targetId, 10);
    if (!numId || numId <= 0) {
      setFeedbackMsg({ text: "Please enter a valid target asset ID.", error: true });
      return;
    }
    if (!reason.trim()) {
      setFeedbackMsg({ text: "Please provide a reason for the restoration.", error: true });
      return;
    }

    try {
      await submitRestoration.mutateAsync({
        archive_id: targetType === "archive" ? numId : null,
        backup_id: targetType === "backup" ? numId : null,
        reason: reason.trim(),
        target_destination: destination.trim() || "/restored",
      });
      setRequestModalOpen(false);
      setReason("");
      setFeedbackMsg({ text: "Restoration request submitted successfully!" });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit restoration request";
      setFeedbackMsg({ text: msg, error: true });
    }
  };

  const handleApprove = async (r: RestorationRequest) => {
    try {
      await decideRestoration.mutateAsync({
        id: r.id,
        payload: {
          decision: "approve",
          comments: "Approved by System Administrator.",
        },
      });
      setFeedbackMsg({ text: `Sensitive restoration #${r.id} approved and executed.` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Approval failed";
      setFeedbackMsg({ text: msg, error: true });
    }
  };

  const handleOpenReject = (r: RestorationRequest) => {
    setSelectedRequest(r);
    setRejectComments("");
    setRejectModalOpen(true);
  };

  const handleConfirmReject = async () => {
    if (!selectedRequest) return;
    if (!rejectComments.trim()) {
      setFeedbackMsg({ text: "Rejection reason is required.", error: true });
      return;
    }
    try {
      await decideRestoration.mutateAsync({
        id: selectedRequest.id,
        payload: {
          decision: "reject",
          comments: rejectComments.trim(),
        },
      });
      setRejectModalOpen(false);
      setSelectedRequest(null);
      setFeedbackMsg({ text: `Restoration request #${selectedRequest.id} rejected.` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Rejection failed";
      setFeedbackMsg({ text: msg, error: true });
    }
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Asset Restoration"
        subtitle="Request archive or backup recovery, track restoration progress, and approve sensitive restorations"
      />

      <Stack gap="lg" mt="md">
        {feedbackMsg && (
          <Alert
            color={feedbackMsg.error ? "red" : "green"}
            icon={feedbackMsg.error ? <FaExclamationCircle /> : <FaCheckCircle />}
            withCloseButton
            onClose={() => setFeedbackMsg(null)}
          >
            {feedbackMsg.text}
          </Alert>
        )}

        <Group justify="flex-end">
          <Button leftSection={<FaPlus />} onClick={() => setRequestModalOpen(true)}>
            Request Restoration
          </Button>
        </Group>

        {/* Sensitive Approvals Panel (Shown when pending) */}
        {pendingApprovals.length > 0 && (
          <Card padding="lg" withBorder radius="md" style={{ borderColor: "#fab005" }}>
            <Group justify="space-between" mb="md">
              <Group>
                <FaShieldAlt size={20} color="#f59f00" />
                <Title order={4} c="yellow.9">
                  Pending Sensitive Restorations ({pendingApprovals.length})
                </Title>
              </Group>
              <Badge color="yellow">SysAdmin Action Required</Badge>
            </Group>

            <Table highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Asset</Table.Th>
                  <Table.Th>Requester</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Destination</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {pendingApprovals.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td fw={600}>#{r.id}</Table.Td>
                    <Table.Td>{r.target_name}</Table.Td>
                    <Table.Td>User {r.requester_user_id}</Table.Td>
                    <Table.Td style={{ maxWidth: 300 }}>
                      <Text size="sm" lineClamp={2}>
                        {r.reason}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs" ff="monospace">
                        {r.target_destination}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="green"
                          leftSection={<FaCheck size={12} />}
                          loading={decideRestoration.isPending}
                          onClick={() => handleApprove(r)}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="light"
                          leftSection={<FaTimes size={12} />}
                          onClick={() => handleOpenReject(r)}
                        >
                          Reject
                        </Button>
                      </Group>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        )}

        {/* All Restorations Table */}
        <Card padding="lg" withBorder radius="md">
          <Title order={4} mb="md">
            Restoration History & Requests
          </Title>

          {isLoading ? (
            <Text c="dimmed">Loading restorations...</Text>
          ) : restorations.length === 0 ? (
            <Text c="dimmed">No restoration requests submitted yet.</Text>
          ) : (
            <Table highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Target Asset</Table.Th>
                  <Table.Th>Classification</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Destination</Table.Th>
                  <Table.Th>Integrity</Table.Th>
                  <Table.Th>Requested At</Table.Th>
                  <Table.Th>Restored At</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {restorations.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td fw={600}>#{r.id}</Table.Td>
                    <Table.Td>{r.target_name}</Table.Td>
                    <Table.Td>
                      {r.is_sensitive ? (
                        <Badge color="red" leftSection={<FaShieldAlt size={10} />}>
                          Sensitive
                        </Badge>
                      ) : (
                        <Badge color="blue">Standard</Badge>
                      )}
                    </Table.Td>
                    <Table.Td>{getRestorationStatusBadge(r.status)}</Table.Td>
                    <Table.Td>
                      <Text size="xs" ff="monospace">
                        {r.target_destination}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      {r.integrity_verified ? (
                        <Badge color="teal">SHA-256 Verified</Badge>
                      ) : (
                        <Badge color="gray">Pending</Badge>
                      )}
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs">{new Date(r.created_at).toLocaleDateString()}</Text>
                    </Table.Td>
                    <Table.Td>
                      {r.restored_at ? (
                        <Text size="xs">{new Date(r.restored_at).toLocaleString()}</Text>
                      ) : (
                        <Text size="xs" c="dimmed">
                          -
                        </Text>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>

      {/* New Restoration Request Modal */}
      <Modal
        opened={requestModalOpen}
        onClose={() => setRequestModalOpen(false)}
        title="Submit Restoration Request"
        size="md"
      >
        <Stack gap="md">
          <Select
            label="Target Type"
            value={targetType}
            onChange={(val) => setTargetType((val as "archive" | "backup") || "archive")}
            data={[
              { value: "archive", label: "Archived Document / File" },
              { value: "backup", label: "System / Dataset Backup" },
            ]}
          />

          <NumberInput
            label={targetType === "archive" ? "Archive ID" : "Backup Execution ID"}
            description="Enter the numeric identifier of the item to recover"
            value={targetId}
            onChange={(val) => setTargetId(val)}
            min={1}
            required
          />

          <TextInput
            label="Target Destination Path"
            value={destination}
            onChange={(e) => setDestination(e.currentTarget.value)}
            required
          />

          <Textarea
            label="Restoration Justification"
            placeholder="Explain why this restored asset is needed..."
            minRows={3}
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            required
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setRequestModalOpen(false)}>
              Cancel
            </Button>
            <Button loading={submitRestoration.isPending} onClick={handleSubmit}>
              Submit Request
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Reject Modal */}
      <Modal
        opened={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Reject Sensitive Restoration Request"
        size="md"
      >
        <Stack gap="md">
          <Text size="sm">
            Provide justification comments for rejecting Restoration #{selectedRequest?.id} for '
            {selectedRequest?.target_name}'.
          </Text>

          <Textarea
            label="Rejection Comments"
            minRows={3}
            placeholder="Security or operational rationale for rejection..."
            value={rejectComments}
            onChange={(e) => setRejectComments(e.currentTarget.value)}
            required
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setRejectModalOpen(false)}>
              Cancel
            </Button>
            <Button
              color="red"
              loading={decideRestoration.isPending}
              onClick={handleConfirmReject}
            >
              Confirm Rejection
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
