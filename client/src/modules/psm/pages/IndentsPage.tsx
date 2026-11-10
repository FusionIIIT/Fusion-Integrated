import React, { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Tooltip,
} from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";
import { CreateIndentModal } from "../components/CreateIndentModal";
import {
  useIndents,
  useIndentVersions,
  useUpdateIndentStatus,
  useWithdrawIndent,
} from "../api/hooks";
import type { Indent, IndentStatus, Priority } from "../api/types";
import { errorMessage } from "../../../lib/http";

export default function IndentsPage() {
  const [activeTab, setActiveTab] = useState<string>("ALL");
  const [modalOpened, setModalOpened] = useState(false);

  // Rejection Dialog state
  const [rejectIndentId, setRejectIndentId] = useState<number | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [rejectionError, setRejectionError] = useState<string | null>(null);

  // History modal state
  const [selectedIndentForHistory, setSelectedIndentForHistory] = useState<number | null>(null);

  const { data: indents = [], isLoading, refetch } = useIndents(
    activeTab !== "ALL" ? { status: activeTab } : undefined
  );

  const { data: versions = [] } = useIndentVersions(selectedIndentForHistory);

  const statusMutation = useUpdateIndentStatus(0);
  const withdrawMutation = useWithdrawIndent(0);

  const handleTransition = async (indentId: number, targetState: IndentStatus, justification = "") => {
    try {
      // Direct call using the hook logic
      await statusMutation.mutateAsync({
        target_state: targetState,
        justification,
      });
      refetch();
    } catch (e: unknown) {
      alert(errorMessage(e));
    }
  };

  const handleWithdraw = async (indentId: number) => {
    if (!window.confirm("Are you sure you want to withdraw this pending indent?")) return;
    try {
      await withdrawMutation.mutateAsync();
      refetch();
    } catch (e: unknown) {
      alert(errorMessage(e));
    }
  };

  const handleConfirmReject = async () => {
    if (!rejectIndentId) return;
    if (!rejectionReason.trim()) {
      setRejectionError("Rejection justification is mandatory.");
      return;
    }
    try {
      await handleTransition(rejectIndentId, "REJECTED", rejectionReason.trim());
      setRejectIndentId(null);
      setRejectionReason("");
      setRejectionError(null);
    } catch (e: unknown) {
      setRejectionError(errorMessage(e));
    }
  };

  const getPriorityBadge = (priority: Priority) => {
    switch (priority) {
      case "CRITICAL":
        return <Badge color="red" variant="filled">CRITICAL</Badge>;
      case "HIGH":
        return <Badge color="orange" variant="light">HIGH</Badge>;
      default:
        return <Badge color="gray" variant="light">NORMAL</Badge>;
    }
  };

  const getStatusBadge = (status: IndentStatus) => {
    switch (status) {
      case "APPROVED":
        return <Badge color="green" variant="filled">APPROVED</Badge>;
      case "REJECTED":
        return <Badge color="red" variant="light">REJECTED</Badge>;
      case "WITHDRAWN":
        return <Badge color="gray" variant="outline">WITHDRAWN</Badge>;
      case "DRAFT":
        return <Badge color="yellow" variant="outline">DRAFT</Badge>;
      default:
        return <Badge color="blue" variant="light">{status.replace(/_/g, " ")}</Badge>;
    }
  };

  return (
    <Stack gap="lg" p="md">
      <PageHeader
        title="Purchase Indents"
        subtitle="Manage material and service requisition workflows, approvals, and duplicate checks."
        action={
          <Button onClick={() => setModalOpened(true)} color="blue">
            + New Indent
          </Button>
        }
      />

      <Tabs value={activeTab} onChange={(val) => setActiveTab(val || "ALL")}>
        <Tabs.List>
          <Tabs.Tab value="ALL">All Indents</Tabs.Tab>
          <Tabs.Tab value="SUBMITTED">Submitted</Tabs.Tab>
          <Tabs.Tab value="STOCK_CHECKED">Stock Checked</Tabs.Tab>
          <Tabs.Tab value="DEPT_REVIEWED">Dept Reviewed</Tabs.Tab>
          <Tabs.Tab value="HEAD_RECOMMENDED">Head Recommended</Tabs.Tab>
          <Tabs.Tab value="AWAITING_FINAL_APPROVAL">Awaiting Final Approval</Tabs.Tab>
          <Tabs.Tab value="APPROVED">Approved</Tabs.Tab>
          <Tabs.Tab value="REJECTED">Rejected</Tabs.Tab>
          <Tabs.Tab value="WITHDRAWN">Withdrawn</Tabs.Tab>
        </Tabs.List>
      </Tabs>

      <Card withBorder radius="md" p={0}>
        <Table striped highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Indent ID</Table.Th>
              <Table.Th>Item Details</Table.Th>
              <Table.Th>Qty</Table.Th>
              <Table.Th>Est. Cost (INR)</Table.Th>
              <Table.Th>Priority</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Flags</Table.Th>
              <Table.Th>Version</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {isLoading ? (
              <Table.Tr>
                <Table.Td colSpan={9} style={{ textAlign: "center", padding: "2rem" }}>
                  Loading Purchase Indents...
                </Table.Td>
              </Table.Tr>
            ) : indents.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={9} style={{ textAlign: "center", padding: "2rem", color: "#888" }}>
                  No indents found matching current filter.
                </Table.Td>
              </Table.Tr>
            ) : (
              indents.map((ind: Indent) => (
                <Table.Tr key={ind.id}>
                  <Table.Td>
                    <Text fw={600} size="sm">{ind.indent_id}</Text>
                    <Text size="xs" c="dimmed">
                      {new Date(ind.created_at).toLocaleDateString()}
                    </Text>
                  </Table.Td>
                  <Table.Td style={{ maxWidth: "250px" }}>
                    <Text size="sm" lineClamp={2}>{ind.item_details}</Text>
                    <Text size="xs" c="dimmed" lineClamp={1}>
                      Reason: {ind.justification}
                    </Text>
                  </Table.Td>
                  <Table.Td>{ind.quantity}</Table.Td>
                  <Table.Td>
                    <Text fw={600}>₹{Number(ind.estimated_cost).toLocaleString("en-IN")}</Text>
                  </Table.Td>
                  <Table.Td>{getPriorityBadge(ind.priority)}</Table.Td>
                  <Table.Td>{getStatusBadge(ind.status)}</Table.Td>
                  <Table.Td>
                    {ind.is_duplicate && (
                      <Tooltip label="Potential duplicate detected against existing active indent!">
                        <Badge color="red" variant="dot">Duplicate?</Badge>
                      </Tooltip>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Button
                      variant="subtle"
                      size="xs"
                      onClick={() => setSelectedIndentForHistory(ind.id)}
                    >
                      v{ind.current_version}
                    </Button>
                  </Table.Td>
                  <Table.Td style={{ textAlign: "right" }}>
                    <Group gap="xs" justify="flex-end">
                      {ind.status === "SUBMITTED" && (
                        <Button
                          size="xs"
                          color="teal"
                          onClick={() => handleTransition(ind.id, "STOCK_CHECKED")}
                        >
                          Check Stock
                        </Button>
                      )}
                      {ind.status === "STOCK_CHECKED" && (
                        <Button
                          size="xs"
                          color="blue"
                          onClick={() => handleTransition(ind.id, "DEPT_REVIEWED")}
                        >
                          Dept Review
                        </Button>
                      )}
                      {ind.status === "DEPT_REVIEWED" && (
                        <Button
                          size="xs"
                          color="indigo"
                          onClick={() => handleTransition(ind.id, "HEAD_RECOMMENDED")}
                        >
                          Recommend
                        </Button>
                      )}
                      {ind.status === "HEAD_RECOMMENDED" && (
                        <Button
                          size="xs"
                          color="cyan"
                          onClick={() => handleTransition(ind.id, "AWAITING_FINAL_APPROVAL")}
                        >
                          Forward Approval
                        </Button>
                      )}
                      {ind.status === "AWAITING_FINAL_APPROVAL" && (
                        <Button
                          size="xs"
                          color="green"
                          onClick={() => handleTransition(ind.id, "APPROVED")}
                        >
                          Sanction Approve
                        </Button>
                      )}
                      {!["APPROVED", "REJECTED", "WITHDRAWN"].includes(ind.status) && (
                        <>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            onClick={() => {
                              setRejectIndentId(ind.id);
                              setRejectionReason("");
                              setRejectionError(null);
                            }}
                          >
                            Reject
                          </Button>
                          <Button
                            size="xs"
                            color="gray"
                            variant="subtle"
                            onClick={() => handleWithdraw(ind.id)}
                          >
                            Withdraw
                          </Button>
                        </>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Create Indent Modal */}
      <CreateIndentModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        onSuccess={() => refetch()}
      />

      {/* Reject Justification Modal */}
      <Modal
        opened={Boolean(rejectIndentId)}
        onClose={() => setRejectIndentId(null)}
        title="Reject Purchase Indent"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            Per Institute Rule BR-PSM-005, a written rejection justification is required when
            refusing an indent.
          </Text>
          {rejectionError && (
            <Text c="red" size="sm">{rejectionError}</Text>
          )}
          <Textarea
            label="Rejection Justification"
            placeholder="Reason for rejecting this requisition..."
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.currentTarget.value)}
            required
            minRows={3}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRejectIndentId(null)}>Cancel</Button>
            <Button color="red" onClick={handleConfirmReject}>Confirm Rejection</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Version History Modal */}
      <Modal
        opened={Boolean(selectedIndentForHistory)}
        onClose={() => setSelectedIndentForHistory(null)}
        title="Indent Version Audit History"
        size="lg"
        centered
      >
        <Stack gap="sm">
          {versions.length === 0 ? (
            <Text size="sm" c="dimmed">No past versions archived.</Text>
          ) : (
            versions.map((ver) => (
              <Card key={ver.id} withBorder p="sm" radius="sm">
                <Group justify="space-between" mb="xs">
                  <Badge color="blue">Version {ver.version_number}</Badge>
                  <Text size="xs" c="dimmed">{new Date(ver.created_at).toLocaleString()}</Text>
                </Group>
                <Text size="sm" fw={600}>{ver.item_details}</Text>
                <Text size="xs">Quantity: {ver.quantity} | Est. Cost: ₹{ver.estimated_cost}</Text>
                <Text size="xs" c="dimmed">Justification: {ver.justification}</Text>
              </Card>
            ))
          )}
        </Stack>
      </Modal>
    </Stack>
  );
}
