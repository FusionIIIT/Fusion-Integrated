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
import { FaPlus, FaTools } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useComplaints,
  useCreateComplaint,
  useHostels,
  useUpdateComplaintStatus,
} from "../api/hooks";
import type { ComplaintCategory, ComplaintSeverity, HostelComplaint } from "../api/types";

export default function ComplaintManagementPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: complaintsData, error: complaintsError } = useComplaints({ hostel_id: hostelId });

  const createComplaint = useCreateComplaint();
  const updateStatus = useUpdateComplaintStatus();

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState<HostelComplaint | null>(null);

  // Form state
  const [cmpHostelId, setCmpHostelId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [category, setCategory] = useState<string>("electrical");
  const [severity, setSeverity] = useState<string>("medium");

  // Status update state
  const [targetStatus, setTargetStatus] = useState<string>("in_progress");
  const [assignedWorker, setAssignedWorker] = useState("");
  const [resolutionNotes, setResolutionNotes] = useState("");

  const handleCreate = async () => {
    if (!cmpHostelId) return;
    try {
      await createComplaint.mutateAsync({
        hostel: Number(cmpHostelId),
        title,
        description,
        location,
        category: category as ComplaintCategory,
        severity: severity as ComplaintSeverity,
      });
      notifications.show({ title: "Success", message: "Complaint logged successfully", color: "green" });
      setCreateModalOpen(false);
      setTitle("");
      setDescription("");
      setLocation("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to submit complaint", color: "red" });
    }
  };

  const handleUpdate = async () => {
    if (!selectedComplaint) return;
    try {
      await updateStatus.mutateAsync({
        id: selectedComplaint.id,
        status: targetStatus,
        assigned_worker: assignedWorker,
        resolution_notes: resolutionNotes,
      });
      notifications.show({ title: "Success", message: "Complaint status updated", color: "green" });
      setStatusModalOpen(false);
      setSelectedComplaint(null);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to update complaint", color: "red" });
    }
  };

  if (complaintsError) return <Container size="xl"><ErrorState error={complaintsError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const complaints = complaintsData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Complaints"
        subtitle="Log facility maintenance issues, assign staff workers, escalate to Warden, and track resolutions"
        action={
          <Button leftSection={<FaPlus size={14} />} onClick={() => setCreateModalOpen(true)}>
            Lodge Complaint
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
              <Table.Th>Complaint</Table.Th>
              <Table.Th>Hostel & Location</Table.Th>
              <Table.Th>Category</Table.Th>
              <Table.Th>Severity</Table.Th>
              <Table.Th>Assigned Staff</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {complaints.map((c) => (
              <Table.Tr key={c.id}>
                <Table.Td>
                  <Text fw={600} size="sm">#{c.id} - {c.title}</Text>
                  <Text size="xs" c="dimmed" lineClamp={1}>{c.description}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{c.hostel_name || `Hostel #${c.hostel}`}</Text>
                  <Text size="xs" c="dimmed">{c.location}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="outline">{c.category.toUpperCase()}</Badge>
                </Table.Td>
                <Table.Td>
                  <Badge color={c.severity === "emergency" || c.severity === "high" ? "red" : c.severity === "medium" ? "orange" : "gray"}>
                    {c.severity.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>{c.assigned_worker || "Unassigned"}</Table.Td>
                <Table.Td>
                  <Badge color={c.status === "resolved" ? "green" : c.status === "escalated" ? "red" : c.status === "in_progress" ? "blue" : "yellow"}>
                    {c.status.toUpperCase()}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    variant="subtle"
                    leftSection={<FaTools size={12} />}
                    onClick={() => {
                      setSelectedComplaint(c);
                      setTargetStatus(c.status);
                      setAssignedWorker(c.assigned_worker || "");
                      setResolutionNotes(c.resolution_notes || "");
                      setStatusModalOpen(true);
                    }}
                  >
                    Update
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Modal: Lodge Complaint */}
      <Modal opened={createModalOpen} onClose={() => setCreateModalOpen(false)} title="Lodge Maintenance Complaint" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={cmpHostelId}
            onChange={setCmpHostelId}
          />
          <TextInput label="Title / Subject" placeholder="e.g. Broken window latch, geyser tripping" required value={title} onChange={(e) => setTitle(e.target.value)} />
          <Select
            label="Category"
            required
            data={[
              { value: "electrical", label: "Electrical" },
              { value: "plumbing", label: "Plumbing" },
              { value: "carpentry", label: "Carpentry" },
              { value: "cleanliness", label: "Cleanliness / Sanitation" },
              { value: "internet", label: "Internet / Wi-Fi" },
              { value: "discipline", label: "Disciplinary" },
              { value: "mess", label: "Mess / Food" },
              { value: "other", label: "Other" },
            ]}
            value={category}
            onChange={(val) => val && setCategory(val)}
          />
          <Select
            label="Severity"
            required
            data={[
              { value: "low", label: "Low (Minor inconvenience)" },
              { value: "medium", label: "Medium (Standard repair)" },
              { value: "high", label: "High (Urgent disruption)" },
              { value: "emergency", label: "Emergency (Safety / Water / Power threat)" },
            ]}
            value={severity}
            onChange={(val) => val && setSeverity(val)}
          />
          <TextInput label="Specific Location / Room Number" placeholder="e.g. Room 204, 2nd floor common washroom" required value={location} onChange={(e) => setLocation(e.target.value)} />
          <Textarea label="Detailed Description" required value={description} onChange={(e) => setDescription(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setCreateModalOpen(false)}>Cancel</Button>
            <Button loading={createComplaint.isPending} onClick={handleCreate}>Submit Complaint</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Update Complaint Status */}
      <Modal opened={statusModalOpen} onClose={() => setStatusModalOpen(false)} title={`Update Complaint #${selectedComplaint?.id}`} centered>
        <Stack gap="sm">
          <Select
            label="Target Status"
            required
            data={[
              { value: "in_progress", label: "In Progress (Assign Staff)" },
              { value: "escalated", label: "Escalate to Warden" },
              { value: "resolved", label: "Resolved" },
              { value: "closed", label: "Closed" },
              { value: "open", label: "Re-Open" },
            ]}
            value={targetStatus}
            onChange={(val) => val && setTargetStatus(val)}
          />
          <TextInput
            label="Assign Maintenance Worker / Technician"
            placeholder="e.g. Electrician Ramu, Plumber Shyam"
            value={assignedWorker}
            onChange={(e) => setAssignedWorker(e.target.value)}
          />
          <Textarea
            label="Resolution Notes / Action Taken"
            placeholder="Repairs completed / parts replaced"
            value={resolutionNotes}
            onChange={(e) => setResolutionNotes(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setStatusModalOpen(false)}>Cancel</Button>
            <Button loading={updateStatus.isPending} onClick={handleUpdate}>Update Complaint</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
