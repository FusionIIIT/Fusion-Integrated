import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FaPlus, FaCheck, FaTimes, FaCalendarAlt } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useHostels,
  useLeaveDecision,
  useLeaves,
  useSubmitLeave,
} from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function LeaveManagementPage() {
  const { can } = useAuth();
  const { data: leaves, isPending: leavesPending, error: leavesError } = useLeaves();
  const { data: hostels } = useHostels();

  const submitMutation = useSubmitLeave();
  const decisionMutation = useLeaveDecision();

  const [activeTab, setActiveTab] = useState<string | null>("all");
  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [selectedLeave, setSelectedLeave] = useState<LeaveRequest | null>(null);
  const [decisionType, setDecisionType] = useState<"approved" | "rejected">("approved");
  const [decisionRemarks, setDecisionRemarks] = useState("");

  // Application form
  const [lHostelId, setLHostelId] = useState<string | null>(null);
  const [lType, setLType] = useState<string | null>("home");
  const [lStart, setLStart] = useState("");
  const [lEnd, setLEnd] = useState("");
  const [lReason, setLReason] = useState("");
  const [lAddress, setLAddress] = useState("");
  const [lEmergency, setLEmergency] = useState("");

  if (leavesError) {
    return (
      <Container size="xl">
        <ErrorState error={leavesError} />
      </Container>
    );
  }

  const handleApply = async () => {
    if (!lHostelId || !lStart || !lEnd || !lReason) return;
    await submitMutation.mutateAsync({
      hostel_id: Number(lHostelId),
      leave_type: lType,
      start_date: lStart,
      end_date: lEnd,
      reason: lReason,
      address_during_leave: lAddress,
      emergency_contact: lEmergency,
    });
    setApplyModalOpen(false);
    setLReason("");
    setLAddress("");
    setLEmergency("");
  };

  const handleDecision = async () => {
    if (!selectedLeave) return;
    await decisionMutation.mutateAsync({
      id: selectedLeave.id,
      decision: decisionType,
      remarks: decisionRemarks,
    });
    setDecisionModalOpen(false);
    setDecisionRemarks("");
  };

  const hostelOptions = (hostels ?? []).map((h) => ({
    value: String(h.id),
    label: `${h.name} (${h.code})`,
  }));

  const pendingLeaves = (leaves ?? []).filter((l) => l.status === "submitted");
  const decidedLeaves = (leaves ?? []).filter((l) => l.status !== "submitted");

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Leave Management"
        subtitle="Manage student leave applications, out-of-station permissions, and caretaker approvals"
        action={
          can("hostel.leave.apply") && (
            <Button leftSection={<FaPlus size={12} />} onClick={() => setApplyModalOpen(true)}>
              Apply for Leave
            </Button>
          )
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab} mb="lg">
        <Tabs.List>
          <Tabs.Tab value="all" leftSection={<FaCalendarAlt size={14} />}>
            All Leaves ({leaves?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="pending" leftSection={<FaCalendarAlt size={14} />}>
            Pending Review ({pendingLeaves.length})
          </Tabs.Tab>
          <Tabs.Tab value="history" leftSection={<FaCalendarAlt size={14} />}>
            Approved / Rejected ({decidedLeaves.length})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value={activeTab || "all"} pt="md">
          <Card withBorder padding="md">
            <DataTable<LeaveRequest>
              rows={
                activeTab === "pending"
                  ? pendingLeaves
                  : activeTab === "history"
                  ? decidedLeaves
                  : leaves ?? []
              }
              loading={leavesPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "roll", header: "Roll Number", render: (r) => <Text fw={600}>{r.student_roll_number}</Text> },
                { key: "name", header: "Student Name", render: (r) => r.student_name },
                { key: "hostel", header: "Hostel", render: (r) => r.hostel_name },
                { key: "type", header: "Type", render: (r) => <Badge color="gray">{r.leave_type.toUpperCase()}</Badge> },
                { key: "duration", header: "Duration", render: (r) => `${r.start_date} → ${r.end_date}` },
                { key: "reason", header: "Reason", render: (r) => r.reason },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => (
                    <Badge color={r.status === "approved" ? "teal" : r.status === "rejected" ? "red" : "blue"}>
                      {r.status.toUpperCase()}
                    </Badge>
                  ),
                },
                {
                  key: "remarks",
                  header: "Decision Remarks",
                  render: (r) => r.decision_remarks || "—",
                },
                {
                  key: "action",
                  header: "Action",
                  render: (r) =>
                    can("hostel.leave.review") && r.status === "submitted" ? (
                      <Group gap="xs">
                        <Button
                          size="xs"
                          color="teal"
                          variant="light"
                          leftSection={<FaCheck size={10} />}
                          onClick={() => {
                            setSelectedLeave(r);
                            setDecisionType("approved");
                            setDecisionModalOpen(true);
                          }}
                        >
                          Approve
                        </Button>
                        <Button
                          size="xs"
                          color="red"
                          variant="subtle"
                          leftSection={<FaTimes size={10} />}
                          onClick={() => {
                            setSelectedLeave(r);
                            setDecisionType("rejected");
                            setDecisionModalOpen(true);
                          }}
                        >
                          Reject
                        </Button>
                      </Group>
                    ) : null,
                },
              ]}
              empty={{
                title: "No Leave Records",
                description: "Student leave applications and approvals will appear here.",
              }}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* APPLY LEAVE MODAL */}
      <Modal opened={applyModalOpen} onClose={() => setApplyModalOpen(false)} title="Submit Hostel Leave Application">
        <Stack gap="sm">
          <Select
            label="Hostel"
            placeholder="Select hostel"
            data={hostelOptions}
            value={lHostelId}
            onChange={setLHostelId}
            required
          />
          <Select
            label="Leave Type"
            data={[
              { value: "home", label: "Home Visit" },
              { value: "academic", label: "Academic / Conference" },
              { value: "medical", label: "Medical Leave" },
              { value: "emergency", label: "Personal Emergency" },
            ]}
            value={lType}
            onChange={setLType}
            required
          />
          <Group grow>
            <TextInput label="Start Date" type="date" required value={lStart} onChange={(e) => setLStart(e.currentTarget.value)} />
            <TextInput label="End Date" type="date" required value={lEnd} onChange={(e) => setLEnd(e.currentTarget.value)} />
          </Group>
          <Textarea label="Reason for Leave" required value={lReason} onChange={(e) => setLReason(e.currentTarget.value)} />
          <TextInput label="Address During Leave" value={lAddress} onChange={(e) => setLAddress(e.currentTarget.value)} />
          <TextInput label="Emergency Contact Phone" value={lEmergency} onChange={(e) => setLEmergency(e.currentTarget.value)} />

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setApplyModalOpen(false)}>Cancel</Button>
            <Button loading={submitMutation.isPending} onClick={handleApply}>Submit Application</Button>
          </Group>
        </Stack>
      </Modal>

      {/* DECISION MODAL */}
      <Modal opened={decisionModalOpen} onClose={() => setDecisionModalOpen(false)} title="Caretaker Leave Decision">
        <Stack gap="sm">
          <Text size="sm">
            Reviewing leave for <b>{selectedLeave?.student_name}</b> ({selectedLeave?.student_roll_number})
          </Text>
          <Text size="xs" c="dimmed">
            Period: {selectedLeave?.start_date} to {selectedLeave?.end_date} ({selectedLeave?.leave_type})
          </Text>
          <TextInput
            label="Remarks / Decision Rationale"
            placeholder="e.g. Approved with parent consent verified"
            value={decisionRemarks}
            onChange={(e) => setDecisionRemarks(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setDecisionModalOpen(false)}>Cancel</Button>
            <Button
              color={decisionType === "approved" ? "teal" : "red"}
              loading={decisionMutation.isPending}
              onClick={handleDecision}
            >
              Confirm {decisionType === "approved" ? "Approval" : "Rejection"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
