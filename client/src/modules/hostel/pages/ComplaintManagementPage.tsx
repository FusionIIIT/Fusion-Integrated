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
import { FaPlus, FaTools, FaEye } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useComplaints,
  useHostels,
  useSubmitComplaint,
  useUpdateComplaintStatus,
} from "../api/hooks";
import type { HostelComplaint } from "../api/types";

export default function ComplaintManagementPage() {
  const { data: hostels } = useHostels();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string | null>("all");

  const {
    data: complaints,
    isPending,
    error,
  } = useComplaints({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
    status: activeTab !== "all" && activeTab !== "escalated" ? activeTab! : undefined,
    escalated_only: activeTab === "escalated" ? true : undefined,
  });

  const submitMutation = useSubmitComplaint();
  const updateMutation = useUpdateComplaintStatus();

  // Lodge complaint modal
  const [lodgeModalOpen, setLodgeModalOpen] = useState(false);
  const [cHostelId, setCHostelId] = useState<string | null>(null);
  const [cRoom, setCRoom] = useState("");
  const [cCategory, setCCategory] = useState<string | null>("electrical");
  const [cTitle, setCTitle] = useState("");
  const [cDescription, setCDescription] = useState("");
  const [cAttachment, setCAttachment] = useState("");

  // Action / Status modal
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState<HostelComplaint | null>(null);
  const [newStatus, setNewStatus] = useState<string | null>("in_progress");
  const [actionTaken, setActionTaken] = useState("");
  const [escalateReason, setEscalateReason] = useState("");

  // Details modal
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleLodge = async () => {
    if (!cHostelId || !cTitle || !cDescription || !cRoom) return;
    await submitMutation.mutateAsync({
      hostel: Number(cHostelId),
      room_number: cRoom,
      category: cCategory || "other",
      title: cTitle,
      description: cDescription,
      attachment_url: cAttachment || "",
    });
    setLodgeModalOpen(false);
    setCRoom("");
    setCTitle("");
    setCDescription("");
    setCAttachment("");
  };

  const handleUpdateStatus = async () => {
    if (!selectedComplaint || !newStatus) return;
    await updateMutation.mutateAsync({
      id: selectedComplaint.id,
      data: {
        status: newStatus,
        action_taken: actionTaken,
        escalation_reason: newStatus === "escalated" ? escalateReason : undefined,
      },
    });
    setActionModalOpen(false);
    setActionTaken("");
    setEscalateReason("");
  };

  const getStatusBadge = (status: string, escalated: boolean) => {
    if (escalated || status === "escalated") {
      return <Badge color="red">Escalated</Badge>;
    }
    switch (status) {
      case "submitted":
        return <Badge color="blue">Submitted</Badge>;
      case "in_progress":
        return <Badge color="yellow">In Progress</Badge>;
      case "resolved":
        return <Badge color="teal">Resolved</Badge>;
      default:
        return <Badge color="gray">{status}</Badge>;
    }
  };

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Hostel Complaint Management"
          subtitle="Track, resolve, and escalate infrastructure and student complaints"
          action={
            <Button
              leftSection={<FaPlus />}
              onClick={() => {
                if (hostels && hostels.length > 0 && hostels[0]) {
                  setCHostelId(String(hostels[0].id));
                }
                setLodgeModalOpen(true);
              }}
            >
              Lodge Complaint
            </Button>
          }
        />

        <Card withBorder radius="md">
          <Group justify="space-between" mb="md">
            <Select
              placeholder="Filter by hostel"
              clearable
              value={selectedHostel}
              onChange={setSelectedHostel}
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              style={{ width: 280 }}
            />

            <Tabs value={activeTab} onChange={setActiveTab}>
              <Tabs.List>
                <Tabs.Tab value="all">All Complaints</Tabs.Tab>
                <Tabs.Tab value="submitted">Submitted</Tabs.Tab>
                <Tabs.Tab value="in_progress">In Progress</Tabs.Tab>
                <Tabs.Tab value="escalated">Escalated</Tabs.Tab>
                <Tabs.Tab value="resolved">Resolved</Tabs.Tab>
              </Tabs.List>
            </Tabs>
          </Group>

          <DataTable<HostelComplaint>
            rows={complaints || []}
            loading={isPending}
            rowKey={(r) => r.id}
            columns={[
              {
                key: "id",
                header: "ID",
                render: (r) => <Text size="sm" fw={600}>#{r.id}</Text>,
              },
              {
                key: "hostel",
                header: "Hostel & Room",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="sm" fw={500}>{r.hostel_name}</Text>
                    <Text size="xs" c="dimmed">Room {r.room_number || "N/A"}</Text>
                  </Stack>
                ),
              },
              {
                key: "student",
                header: "Student",
                render: (r) => (
                  <Stack gap={2}>
                    <Text size="sm">{r.student_name || "Unknown"}</Text>
                    <Text size="xs" c="dimmed">{r.student_roll_number}</Text>
                  </Stack>
                ),
              },
              {
                key: "category",
                header: "Category & Title",
                render: (r) => (
                  <Stack gap={2}>
                    <Badge size="xs" variant="outline">{r.category}</Badge>
                    <Text size="sm" fw={500} lineClamp={1}>{r.title}</Text>
                  </Stack>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (r) => getStatusBadge(r.status, r.escalated_to_warden),
              },
              {
                key: "date",
                header: "Date",
                render: (r) => (
                  <Text size="xs" c="dimmed">
                    {new Date(r.created_at).toLocaleDateString()}
                  </Text>
                ),
              },
              {
                key: "actions",
                header: "Actions",
                render: (r) => (
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<FaEye />}
                      onClick={() => {
                        setSelectedComplaint(r);
                        setDetailsModalOpen(true);
                      }}
                    >
                      View
                    </Button>
                    {r.status !== "resolved" && (
                      <Button
                        size="xs"
                        variant="outline"
                        leftSection={<FaTools />}
                        onClick={() => {
                          setSelectedComplaint(r);
                          setNewStatus(r.status === "submitted" ? "in_progress" : "resolved");
                          setActionTaken(r.action_taken || "");
                          setEscalateReason(r.escalation_reason || "");
                          setActionModalOpen(true);
                        }}
                      >
                        Update
                      </Button>
                    )}
                  </Group>
                ),
              },
            ]}
            empty={{
              title: "No Complaints Found",
              description: "No complaints recorded matching the selected filter.",
            }}
          />
        </Card>

        {/* Modal: Lodge Complaint */}
        <Modal
          opened={lodgeModalOpen}
          onClose={() => setLodgeModalOpen(false)}
          title="Lodge Hostel Complaint"
          size="lg"
        >
          <Stack gap="sm">
            <Select
              label="Hostel"
              required
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              value={cHostelId}
              onChange={setCHostelId}
            />

            <Group grow>
              <TextInput
                label="Room Number"
                required
                placeholder="e.g. A-102"
                value={cRoom}
                onChange={(e) => setCRoom(e.target.value)}
              />
              <Select
                label="Category"
                required
                data={[
                  { value: "electrical", label: "Electrical" },
                  { value: "plumbing", label: "Plumbing" },
                  { value: "carpentry", label: "Carpentry" },
                  { value: "cleanliness", label: "Cleanliness" },
                  { value: "internet", label: "Internet / Wi-Fi" },
                  { value: "discipline", label: "Discipline" },
                  { value: "other", label: "Other" },
                ]}
                value={cCategory}
                onChange={setCCategory}
              />
            </Group>

            <TextInput
              label="Subject / Title"
              required
              placeholder="Brief summary of the defect or issue"
              value={cTitle}
              onChange={(e) => setCTitle(e.target.value)}
            />

            <Textarea
              label="Detailed Description"
              required
              minRows={3}
              placeholder="Provide complete details to help caretakers/technicians reproduce and repair..."
              value={cDescription}
              onChange={(e) => setCDescription(e.target.value)}
            />

            <TextInput
              label="Attachment / Photo URL (Optional)"
              placeholder="https://... or document link"
              value={cAttachment}
              onChange={(e) => setCAttachment(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setLodgeModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={submitMutation.isPending}
                disabled={!cHostelId || !cTitle || !cDescription || !cRoom}
                onClick={handleLodge}
              >
                Submit Complaint
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Update Complaint Status */}
        <Modal
          opened={actionModalOpen}
          onClose={() => setActionModalOpen(false)}
          title={`Update Complaint #${selectedComplaint?.id}`}
          size="md"
        >
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              Title: <Text span fw={500}>{selectedComplaint?.title}</Text>
            </Text>

            <Select
              label="Target Status"
              required
              data={[
                { value: "in_progress", label: "In Progress (Assigned / Under Repair)" },
                { value: "resolved", label: "Resolved (Work Completed)" },
                { value: "escalated", label: "Escalate to Warden" },
              ]}
              value={newStatus}
              onChange={setNewStatus}
            />

            {newStatus === "resolved" && (
              <Textarea
                label="Action Taken / Resolution Summary"
                required
                minRows={3}
                placeholder="Describe repairs conducted, parts replaced, technician details..."
                value={actionTaken}
                onChange={(e) => setActionTaken(e.target.value)}
              />
            )}

            {newStatus === "escalated" && (
              <Textarea
                label="Escalation Reason for Warden"
                required
                minRows={3}
                placeholder="Explain why this requires Warden intervention (e.g. repeated failure, high expense, disciplinary)..."
                value={escalateReason}
                onChange={(e) => setEscalateReason(e.target.value)}
              />
            )}

            {newStatus === "in_progress" && (
              <TextInput
                label="Work Note / Assigned Contractor"
                placeholder="e.g. Electrician Sharma visiting at 4 PM"
                value={actionTaken}
                onChange={(e) => setActionTaken(e.target.value)}
              />
            )}

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setActionModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={updateMutation.isPending}
                onClick={handleUpdateStatus}
              >
                Save Status
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: View Details */}
        <Modal
          opened={detailsModalOpen}
          onClose={() => setDetailsModalOpen(false)}
          title={`Complaint Details #${selectedComplaint?.id}`}
          size="lg"
        >
          {selectedComplaint && (
            <Stack gap="sm">
              <Group justify="space-between">
                <Text size="lg" fw={600}>{selectedComplaint.title}</Text>
                {getStatusBadge(selectedComplaint.status, selectedComplaint.escalated_to_warden)}
              </Group>

              <Group grow>
                <Card withBorder p="xs">
                  <Text size="xs" c="dimmed">Hostel</Text>
                  <Text size="sm" fw={500}>{selectedComplaint.hostel_name}</Text>
                </Card>
                <Card withBorder p="xs">
                  <Text size="xs" c="dimmed">Room</Text>
                  <Text size="sm" fw={500}>{selectedComplaint.room_number || "N/A"}</Text>
                </Card>
                <Card withBorder p="xs">
                  <Text size="xs" c="dimmed">Category</Text>
                  <Text size="sm" fw={500}>{selectedComplaint.category}</Text>
                </Card>
              </Group>

              <Card withBorder p="xs">
                <Text size="xs" c="dimmed">Submitted By</Text>
                <Text size="sm">{selectedComplaint.student_name} ({selectedComplaint.student_roll_number})</Text>
                <Text size="xs" c="dimmed">{new Date(selectedComplaint.created_at).toLocaleString()}</Text>
              </Card>

              <Card withBorder p="sm">
                <Text size="xs" c="dimmed" mb={4}>Description</Text>
                <Text size="sm">{selectedComplaint.description}</Text>
              </Card>

              {selectedComplaint.attachment_url && (
                <Card withBorder p="xs">
                  <Text size="xs" c="dimmed">Attachment</Text>
                  <Text
                    component="a"
                    href={selectedComplaint.attachment_url}
                    target="_blank"
                    size="sm"
                    c="blue"
                  >
                    {selectedComplaint.attachment_url}
                  </Text>
                </Card>
              )}

              {selectedComplaint.escalated_to_warden && (
                <Card withBorder p="sm" bg="red.0">
                  <Text size="xs" c="red" fw={600}>Escalated to Warden</Text>
                  <Text size="sm">{selectedComplaint.escalation_reason || "Escalated for administrative review."}</Text>
                  {selectedComplaint.escalated_at && (
                    <Text size="xs" c="dimmed">
                      Escalated at: {new Date(selectedComplaint.escalated_at).toLocaleString()}
                    </Text>
                  )}
                </Card>
              )}

              {selectedComplaint.action_taken && (
                <Card withBorder p="sm" bg="teal.0">
                  <Text size="xs" c="teal" fw={600}>Action Taken / Resolution</Text>
                  <Text size="sm">{selectedComplaint.action_taken}</Text>
                  {selectedComplaint.resolved_at && (
                    <Text size="xs" c="dimmed">
                      Resolved at: {new Date(selectedComplaint.resolved_at).toLocaleString()}
                    </Text>
                  )}
                </Card>
              )}

              <Group justify="flex-end" mt="md">
                <Button variant="default" onClick={() => setDetailsModalOpen(false)}>
                  Close
                </Button>
              </Group>
            </Stack>
          )}
        </Modal>
      </Stack>
    </Container>
  );
}
