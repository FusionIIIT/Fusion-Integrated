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
  Progress,
  Stack,
  Table,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { FaCheck, FaExclamationTriangle, FaPlus, FaServer, FaTimes } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useStorageExtensionDecision,
  useStorageExtensions,
  useSubmitStorageExtension,
  useUserQuota,
} from "../api";
import type { StorageExtensionRequest } from "../api";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 MB";
  const mb = bytes / (1024 * 1024);
  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(2)} GB`;
  }
  return `${mb.toFixed(1)} MB`;
}

function getStatusBadge(status: string) {
  switch (status) {
    case "submitted":
      return <Badge color="blue">Pending HoD Review</Badge>;
    case "hod_approved":
      return <Badge color="green">HoD Approved</Badge>;
    case "rejected":
      return <Badge color="red">Rejected</Badge>;
    default:
      return <Badge color="gray">{status}</Badge>;
  }
}

export default function StoragePage() {
  const { data: quota } = useUserQuota();
  const { data: extensionsData, isLoading: extensionsLoading } = useStorageExtensions();
  const submitExtension = useSubmitStorageExtension();
  const decideExtension = useStorageExtensionDecision();

  // New Extension Request modal state
  const [requestModalOpen, setRequestModalOpen] = useState(false);
  const [requestedMb, setRequestedMb] = useState<number | string>(500);
  const [reason, setReason] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Reject modal state
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [targetRequest, setTargetRequest] = useState<StorageExtensionRequest | null>(null);
  const [rejectComments, setRejectComments] = useState("");

  const extensions = extensionsData?.results || [];

  // Quota calculation
  const allocated = quota?.allocated_bytes || 0;
  const used = quota?.used_bytes || 0;
  const remaining = quota?.remaining_bytes || 0;
  const usedPercentage = allocated > 0 ? Math.min(100, Math.round((used / allocated) * 100)) : 0;

  const progressColor = usedPercentage > 90 ? "red" : usedPercentage > 70 ? "orange" : "blue";

  const handleSubmitRequest = async () => {
    setErrorMsg(null);
    const mbNum = typeof requestedMb === "number" ? requestedMb : parseInt(requestedMb, 10);
    if (!mbNum || mbNum <= 0) {
      setErrorMsg("Please specify a positive number of megabytes.");
      return;
    }
    if (!reason.trim()) {
      setErrorMsg("Please provide a justification for this storage quota extension.");
      return;
    }

    try {
      await submitExtension.mutateAsync({
        requested_bytes: mbNum * 1024 * 1024,
        reason: reason.trim(),
      });
      setRequestModalOpen(false);
      setRequestedMb(500);
      setReason("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit storage extension request";
      setErrorMsg(msg);
    }
  };

  const handleApprove = async (req: StorageExtensionRequest) => {
    await decideExtension.mutateAsync({
      id: req.id,
      payload: {
        decision: "approve",
        comments: "Approved by Head of Department.",
      },
    });
  };

  const handleOpenReject = (req: StorageExtensionRequest) => {
    setTargetRequest(req);
    setRejectComments("");
    setRejectModalOpen(true);
  };

  const handleConfirmReject = async () => {
    if (!targetRequest) return;
    if (!rejectComments.trim()) {
      setErrorMsg("Comments are required when rejecting a storage extension request.");
      return;
    }
    await decideExtension.mutateAsync({
      id: targetRequest.id,
      payload: {
        decision: "reject",
        comments: rejectComments.trim(),
      },
    });
    setRejectModalOpen(false);
    setTargetRequest(null);
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Storage Quota & Extensions"
        subtitle="Monitor storage allocation, utilization, and manage departmental quota extensions"
      />

      <Stack gap="lg" mt="md">
        {/* Storage Quota Card */}
        <Card padding="lg" withBorder radius="md">
          <Group justify="space-between" mb="xs">
            <Group>
              <FaServer size={22} color="#1c7ed6" />
              <div>
                <Title order={4}>Current Quota Allocation</Title>
                <Text size="sm" c="dimmed">
                  Department: <strong>{quota?.department || "General"}</strong>
                </Text>
              </div>
            </Group>
            <Button
              leftSection={<FaPlus />}
              onClick={() => {
                setErrorMsg(null);
                setRequestModalOpen(true);
              }}
            >
              Request Quota Extension
            </Button>
          </Group>

          <Progress value={usedPercentage} color={progressColor} size="xl" radius="xl" my="md" />

          <Group justify="space-between" mt="xs">
            <div>
              <Text size="xs" c="dimmed">
                Used Capacity
              </Text>
              <Text fw={600}>{formatBytes(used)}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">
                Remaining Capacity
              </Text>
              <Text fw={600} c={remaining < 100 * 1024 * 1024 ? "red" : "inherit"}>
                {formatBytes(remaining)}
              </Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">
                Total Quota
              </Text>
              <Text fw={600}>{formatBytes(allocated)}</Text>
            </div>
            <div>
              <Text size="xs" c="dimmed">
                Utilization
              </Text>
              <Badge color={progressColor} size="lg">
                {usedPercentage}% Consumed
              </Badge>
            </div>
          </Group>
        </Card>

        {/* Extension Requests Table */}
        <Card padding="lg" withBorder radius="md">
          <Title order={4} mb="md">
            Storage Extension Requests
          </Title>

          {extensionsLoading ? (
            <Text c="dimmed">Loading storage extension requests...</Text>
          ) : extensions.length === 0 ? (
            <Text c="dimmed">No storage quota extension requests found.</Text>
          ) : (
            <Table highlightOnHover withTableBorder>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>User ID</Table.Th>
                  <Table.Th>Department</Table.Th>
                  <Table.Th>Requested Capacity</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Reason / Justification</Table.Th>
                  <Table.Th>Decision Info</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {extensions.map((req) => (
                  <Table.Tr key={req.id}>
                    <Table.Td fw={600}>#{req.id}</Table.Td>
                    <Table.Td>User {req.user_id}</Table.Td>
                    <Table.Td>{req.department}</Table.Td>
                    <Table.Td>+{formatBytes(req.requested_bytes)}</Table.Td>
                    <Table.Td>{getStatusBadge(req.status)}</Table.Td>
                    <Table.Td style={{ maxWidth: 300 }}>
                      <Text size="sm" lineClamp={2}>
                        {req.reason}
                      </Text>
                    </Table.Td>
                    <Table.Td>
                      {req.decided_at ? (
                        <div>
                          <Text size="xs" c="dimmed">
                            {new Date(req.decided_at).toLocaleDateString()}
                          </Text>
                          {req.hod_comments && (
                            <Text size="xs" fs="italic">
                              "{req.hod_comments}"
                            </Text>
                          )}
                        </div>
                      ) : (
                        <Text size="xs" c="dimmed">
                          Awaiting decision
                        </Text>
                      )}
                    </Table.Td>
                    <Table.Td>
                      {req.status === "submitted" && (
                        <Group gap="xs">
                          <Button
                            size="xs"
                            color="green"
                            leftSection={<FaCheck size={12} />}
                            loading={decideExtension.isPending}
                            onClick={() => handleApprove(req)}
                          >
                            Approve
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            leftSection={<FaTimes size={12} />}
                            onClick={() => handleOpenReject(req)}
                          >
                            Reject
                          </Button>
                        </Group>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>

      {/* Request Quota Extension Modal */}
      <Modal
        opened={requestModalOpen}
        onClose={() => setRequestModalOpen(false)}
        title="Request Storage Quota Extension"
        size="md"
      >
        <Stack gap="md">
          {errorMsg && (
            <Alert color="red" icon={<FaExclamationTriangle />}>
              {errorMsg}
            </Alert>
          )}

          <Text size="sm">
            Current allocated quota: <strong>{formatBytes(allocated)}</strong>
          </Text>

          <NumberInput
            label="Additional Storage Needed (MB)"
            description="Enter the additional capacity required in megabytes (e.g. 1024 for 1 GB)"
            min={100}
            step={100}
            value={requestedMb}
            onChange={(val) => setRequestedMb(val)}
            required
          />

          <Textarea
            label="Justification Reason"
            description="Explain why additional storage is needed for academic or institutional projects"
            minRows={3}
            placeholder="e.g. Additional storage required for PhD computer vision research datasets..."
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
            required
          />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setRequestModalOpen(false)}>
              Cancel
            </Button>
            <Button loading={submitExtension.isPending} onClick={handleSubmitRequest}>
              Submit Request
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Reject Reason Modal */}
      <Modal
        opened={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Reject Storage Extension Request"
        size="md"
      >
        <Stack gap="md">
          <Text size="sm">
            Please provide a specific reason for rejecting User {targetRequest?.user_id}'s request
            for +{formatBytes(targetRequest?.requested_bytes || 0)}.
          </Text>

          <Textarea
            label="Rejection Comments"
            placeholder="Provide feedback explaining why this quota extension cannot be granted..."
            minRows={3}
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
              loading={decideExtension.isPending}
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
