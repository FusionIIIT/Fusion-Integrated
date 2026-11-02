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
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateSecurityShift, useHostels, useSecurityShifts } from "../api/hooks";
import type { SecurityShiftType } from "../api/types";

export default function SecurityShiftsPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: shiftsData, error: shiftsError } = useSecurityShifts({ hostel_id: hostelId });

  const createShift = useCreateSecurityShift();
  const [shiftModalOpen, setShiftModalOpen] = useState(false);

  // Form state
  const [shiftHostelId, setShiftHostelId] = useState<string | null>(null);
  const [guardName, setGuardName] = useState("");
  const [shiftDate, setShiftDate] = useState(new Date().toISOString().slice(0, 10));
  const [shiftType, setShiftType] = useState<string>("night");
  const [checkpoint, setCheckpoint] = useState("Main Entrance");
  const [contactNumber, setContactNumber] = useState("");
  const [supervisorNotes, setSupervisorNotes] = useState("");

  const handleCreate = async () => {
    if (!shiftHostelId) return;
    try {
      await createShift.mutateAsync({
        hostel: Number(shiftHostelId),
        guard_name: guardName,
        shift_date: shiftDate,
        shift_type: shiftType as SecurityShiftType,
        checkpoint_location: checkpoint,
        contact_number: contactNumber,
        supervisor_notes: supervisorNotes,
      });
      notifications.show({ title: "Success", message: "Security shift scheduled", color: "green" });
      setShiftModalOpen(false);
      setGuardName("");
      setContactNumber("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to schedule shift", color: "red" });
    }
  };

  if (shiftsError) return <Container size="xl"><ErrorState error={shiftsError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const shifts = shiftsData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Security Roster"
        subtitle="Manage perimeter security personnel, checkpoint assignments, and shift rosters"
        action={
          <Button leftSection={<FaPlus size={14} />} onClick={() => setShiftModalOpen(true)}>
            Schedule Security Shift
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
              <Table.Th>Guard Name</Table.Th>
              <Table.Th>Hostel</Table.Th>
              <Table.Th>Date</Table.Th>
              <Table.Th>Shift Type</Table.Th>
              <Table.Th>Checkpoint</Table.Th>
              <Table.Th>Contact</Table.Th>
              <Table.Th>Supervisor Notes</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {shifts.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td fw={600}>{s.guard_name}</Table.Td>
                <Table.Td>{s.hostel_name || `Hostel #${s.hostel}`}</Table.Td>
                <Table.Td>{s.shift_date}</Table.Td>
                <Table.Td>
                  <Badge color={s.shift_type === "night" ? "indigo" : s.shift_type === "evening" ? "orange" : "blue"}>
                    {s.shift_type.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>{s.checkpoint_location}</Table.Td>
                <Table.Td>{s.contact_number}</Table.Td>
                <Table.Td>{s.supervisor_notes || "—"}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Modal: Schedule Shift */}
      <Modal opened={shiftModalOpen} onClose={() => setShiftModalOpen(false)} title="Schedule Guard Shift" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={shiftHostelId}
            onChange={setShiftHostelId}
          />
          <TextInput label="Security Guard Name" required value={guardName} onChange={(e) => setGuardName(e.target.value)} />
          <TextInput label="Shift Date" type="date" required value={shiftDate} onChange={(e) => setShiftDate(e.target.value)} />
          <Select
            label="Shift Type"
            required
            data={[
              { value: "morning", label: "Morning (06:00 - 14:00)" },
              { value: "evening", label: "Evening (14:00 - 22:00)" },
              { value: "night", label: "Night (22:00 - 06:00)" },
              { value: "patrol", label: "Patrol / Roaming" },
            ]}
            value={shiftType}
            onChange={(val) => val && setShiftType(val)}
          />
          <TextInput label="Checkpoint Location" placeholder="e.g. Main Gate, South Wing, Cycle Stand" required value={checkpoint} onChange={(e) => setCheckpoint(e.target.value)} />
          <TextInput label="Contact Mobile" placeholder="10-digit number" required value={contactNumber} onChange={(e) => setContactNumber(e.target.value)} />
          <TextInput label="Supervisor Brief / Special Instructions" placeholder="Visitor checking, gate lock time" value={supervisorNotes} onChange={(e) => setSupervisorNotes(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setShiftModalOpen(false)}>Cancel</Button>
            <Button loading={createShift.isPending} onClick={handleCreate}>Save Roster</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
