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
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaPlus, FaTimes } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateLeave, useDecideLeave, useHostels, useLeaves } from "../api/hooks";
import type { HostelLeave } from "../api/types";

export default function LeaveManagementPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: leavesData, error: leavesError } = useLeaves({ hostel_id: hostelId });

  const createLeave = useCreateLeave();
  const decideLeave = useDecideLeave();

  const [applyModalOpen, setApplyModalOpen] = useState(false);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [selectedLeave, setSelectedLeave] = useState<HostelLeave | null>(null);
  const [decisionType, setDecisionType] = useState<"approved" | "rejected">("approved");
  const [decisionRemarks, setDecisionRemarks] = useState("");

  // Leave form state
  const [leaveHostelId, setLeaveHostelId] = useState<string | null>(null);
  const [leaveType, setLeaveType] = useState<string>("home");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [reason, setReason] = useState("");
  const [destination, setDestination] = useState("");
  const [emergencyContact, setEmergencyContact] = useState("");

  const handleApply = async () => {
    if (!leaveHostelId) return;
    try {
      await createLeave.mutateAsync({
        hostel: Number(leaveHostelId),
        leave_type: leaveType as any,
        from_date: fromDate,
        to_date: toDate,
        reason,
        destination,
        emergency_contact: emergencyContact,
      });
      notifications.show({ title: "Success", message: "Leave request submitted", color: "green" });
      setApplyModalOpen(false);
      setReason("");
      setDestination("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to submit leave", color: "red" });
    }
  };

  const handleDecision = async () => {
    if (!selectedLeave) return;
    try {
      await decideLeave.mutateAsync({
        id: selectedLeave.id,
        decision: decisionType,
        remarks: decisionRemarks,
      });
      notifications.show({ title: "Success", message: `Leave marked as ${decisionType}`, color: "green" });
      setDecisionModalOpen(false);
      setSelectedLeave(null);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to record decision", color: "red" });
    }
  };

  if (leavesError) return <Container size="xl"><ErrorState error={leavesError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const leaves = leavesData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Management"
        subtitle="Submit student out-of-station leave requests, track approvals, and emergency contacts"
        action={
          <Button leftSection={<FaPlus size={14} />} onClick={() => setApplyModalOpen(true)}>
            Apply for Leave
          </Button>
        }
      />

      <Group mb="md">
        <Select
          placeholder="Filter by hostel"
          clearable
          data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
          value={selectedHostel}
          onChange={setSelectedHostel}
          style={{ width: 280 }}
        />
      </Group>

      <Card withBorder radius="md">
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Student</Table.Th>
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Duration</Table.Th>
              <Table.Th>Destination & Contact</Table.Th>
              <Table.Th>Reason</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Review Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {leaves.map((l) => (
              <Table.Tr key={l.id}>
                <Table.Td fw={600}>{l.student_name || `Student #${l.student_user_id}`}</Table.Td>
                <Table.Td>{l.hostel_name || `Hostel #${l.hostel}`}</Table.Td>
                <Table.Td>
                  <Badge variant="outline">{l.leave_type.toUpperCase()}</Badge>
                </Table.Td>
                <Table.Td>
                  {l.from_date} to {l.to_date}
                </Table.Td>
                <Table.Td>
                  <Text size="xs">{l.destination || "N/A"}</Text>
                  <Text size="xs" c="dimmed">Ph: {l.emergency_contact || "N/A"}</Text>
                </Table.Td>
                <Table.Td>{l.reason}</Table.Td>
                <Table.Td>
                  <Badge color={l.status === "approved" ? "green" : l.status === "pending" ? "yellow" : "red"}>
                    {l.status.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {l.status === "pending" && (
                    <Group gap="xs">
                      <Button
                        size="xs"
                        color="green"
                        variant="subtle"
                        leftSection={<FaCheck size={12} />}
                        onClick={() => {
                          setSelectedLeave(l);
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
                        leftSection={<FaTimes size={12} />}
                        onClick={() => {
                          setSelectedLeave(l);
                          setDecisionType("rejected");
                          setDecisionModalOpen(true);
                        }}
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
      </Card>

      {/* Modal: Apply for Leave */}
      <Modal opened={applyModalOpen} onClose={() => setApplyModalOpen(false)} title="Apply for Hostel Leave" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={leaveHostelId}
            onChange={setLeaveHostelId}
          />
          <Select
            label="Leave Type"
            required
            data={[
              { value: "home", label: "Home Visit" },
              { value: "casual", label: "Casual Leave" },
              { value: "medical", label: "Medical Leave" },
              { value: "academic", label: "Academic / Conference" },
              { value: "emergency", label: "Emergency" },
            ]}
            value={leaveType}
            onChange={(val) => val && setLeaveType(val)}
          />
          <Group grow>
            <TextInput label="From Date" type="date" required value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
            <TextInput label="To Date" type="date" required value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </Group>
          <TextInput label="Destination Address / City" placeholder="e.g. Home address" required value={destination} onChange={(e) => setDestination(e.target.value)} />
          <TextInput label="Emergency Contact Number" placeholder="10-digit mobile number" required value={emergencyContact} onChange={(e) => setEmergencyContact(e.target.value)} />
          <Textarea label="Reason for Leave" required value={reason} onChange={(e) => setReason(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setApplyModalOpen(false)}>Cancel</Button>
            <Button loading={createLeave.isPending} onClick={handleApply}>Submit Application</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Decision */}
      <Modal opened={decisionModalOpen} onClose={() => setDecisionModalOpen(false)} title={`Record Leave Decision: ${decisionType.toUpperCase()}`} centered>
        <Stack gap="sm">
          <Text size="sm">
            Leave Request for Student #{selectedLeave?.student_user_id} from {selectedLeave?.from_date} to {selectedLeave?.to_date}.
          </Text>
          <Textarea label="Decision Remarks" placeholder="Approved by caretaker / reason for rejection" value={decisionRemarks} onChange={(e) => setDecisionRemarks(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setDecisionModalOpen(false)}>Cancel</Button>
            <Button color={decisionType === "approved" ? "green" : "red"} loading={decideLeave.isPending} onClick={handleDecision}>
              Confirm {decisionType.toUpperCase()}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
