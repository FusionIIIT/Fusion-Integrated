import { useState } from "react";
import {
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
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaReceipt } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateFine, useFines, useHostels, useUpdateFineStatus } from "../api/hooks";
import type { HostelFine } from "../api/types";

export default function FineManagementPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: finesData, error: finesError } = useFines({ hostel_id: hostelId });

  const createFine = useCreateFine();
  const updateStatus = useUpdateFineStatus();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [updateModalOpen, setUpdateModalOpen] = useState(false);
  const [selectedFine, setSelectedFine] = useState<HostelFine | null>(null);

  // Form state
  const [fineHostelId, setFineHostelId] = useState<string | null>(null);
  const [studentId, setStudentId] = useState<number | string>(1001);
  const [amount, setAmount] = useState<number | string>(500);
  const [reason, setReason] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [remarks, setRemarks] = useState("");

  // Update state
  const [targetStatus, setTargetStatus] = useState<string>("paid");
  const [receiptRef, setReceiptRef] = useState("");
  const [updateRemarks, setUpdateRemarks] = useState("");

  const handleCreate = async () => {
    if (!fineHostelId) return;
    try {
      await createFine.mutateAsync({
        hostel: Number(fineHostelId),
        student_user_id: Number(studentId),
        amount: Number(amount),
        reason,
        due_date: dueDate || undefined,
        remarks,
      });
      notifications.show({ title: "Success", message: "Disciplinary fine imposed", color: "green" });
      setCreateModalOpen(false);
      setReason("");
      setRemarks("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to impose fine", color: "red" });
    }
  };

  const handleUpdate = async () => {
    if (!selectedFine) return;
    if (targetStatus === "paid" && !receiptRef.trim()) {
      notifications.show({ title: "Validation Error", message: "Receipt reference is mandatory to clear fine", color: "red" });
      return;
    }

    try {
      await updateStatus.mutateAsync({
        id: selectedFine.id,
        status: targetStatus,
        receipt_reference: receiptRef,
        remarks: updateRemarks,
      });
      notifications.show({ title: "Success", message: "Fine status updated", color: "green" });
      setUpdateModalOpen(false);
      setSelectedFine(null);
      setReceiptRef("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to update fine", color: "red" });
    }
  };

  if (finesError) return <Container size="xl"><ErrorState error={finesError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const fines = finesData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Fines & Disciplinary"
        subtitle="Manage disciplinary fine impositions, dues tracking, payment receipts, and waiver justifications"
        action={
          <Button leftSection={<FaPlus size={14} />} onClick={() => setCreateModalOpen(true)}>
            Impose Disciplinary Fine
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
              <Table.Th>Amount</Table.Th>
              <Table.Th>Reason & Infraction</Table.Th>
              <Table.Th>Issued / Due Date</Table.Th>
              <Table.Th>Receipt Ref</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {fines.map((f) => (
              <Table.Tr key={f.id}>
                <Table.Td fw={600}>{f.student_name || `Student #${f.student_user_id}`}</Table.Td>
                <Table.Td>{f.hostel_name || `Hostel #${f.hostel}`}</Table.Td>
                <Table.Td fw={700}>Rs. {f.amount}</Table.Td>
                <Table.Td>
                  <Text size="sm">{f.reason}</Text>
                  {f.remarks && <Text size="xs" c="dimmed">{f.remarks}</Text>}
                </Table.Td>
                <Table.Td>
                  <Text size="xs">Issued: {f.issued_date}</Text>
                  {f.due_date && <Text size="xs" c="red">Due: {f.due_date}</Text>}
                </Table.Td>
                <Table.Td>
                  <Text size="xs" fw={500}>{f.receipt_reference || "—"}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={f.status === "paid" ? "green" : f.status === "waived" ? "gray" : "red"}>
                    {f.status.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  {f.status === "pending" && (
                    <Button
                      size="xs"
                      variant="subtle"
                      leftSection={<FaReceipt size={12} />}
                      onClick={() => {
                        setSelectedFine(f);
                        setTargetStatus("paid");
                        setReceiptRef("");
                        setUpdateModalOpen(true);
                      }}
                    >
                      Record Payment
                    </Button>
                  )}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Modal: Impose Fine */}
      <Modal opened={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Impose Disciplinary Fine" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={fineHostelId}
            onChange={setFineHostelId}
          />
          <NumberInput label="Student User ID" required value={studentId} onChange={setStudentId} />
          <NumberInput label="Fine Amount (Rs.)" min={1} required value={amount} onChange={setAmount} />
          <TextInput label="Reason for Fine" placeholder="e.g. Damage to hostel property, ragging, unauthorized guest" required value={reason} onChange={(e) => setReason(e.target.value)} />
          <TextInput label="Due Date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          <Textarea label="Incident Remarks / Disciplinary Report" value={remarks} onChange={(e) => setRemarks(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateModalOpen(false)}>Cancel</Button>
            <Button color="red" loading={createFine.isPending} onClick={handleCreate}>Impose Fine</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Record Payment or Waiver */}
      <Modal opened={updateModalOpen} onClose={() => setUpdateModalOpen(false)} title={`Update Fine #${selectedFine?.id}`} centered>
        <Stack gap="sm">
          <Text size="sm">
            Disciplinary fine of Rs. {selectedFine?.amount} for Student #{selectedFine?.student_user_id} ({selectedFine?.reason})
          </Text>
          <Select
            label="Resolution Status"
            required
            data={[
              { value: "paid", label: "Paid (Clear Dues with Receipt)" },
              { value: "waived", label: "Waived by Warden / Director" },
            ]}
            value={targetStatus}
            onChange={(val) => val && setTargetStatus(val)}
          />
          {targetStatus === "paid" && (
            <TextInput
              label="Payment Receipt Reference (SBI Collect / Transaction ID)"
              placeholder="e.g. DU12345678, SBI-REC-98234"
              required
              value={receiptRef}
              onChange={(e) => setReceiptRef(e.target.value)}
            />
          )}
          <Textarea label="Payment / Waiver Notes" placeholder="Receipt verification / waiver justification" value={updateRemarks} onChange={(e) => setUpdateRemarks(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setUpdateModalOpen(false)}>Cancel</Button>
            <Button color={targetStatus === "paid" ? "green" : "gray"} loading={updateStatus.isPending} onClick={handleUpdate}>
              Save Status
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
