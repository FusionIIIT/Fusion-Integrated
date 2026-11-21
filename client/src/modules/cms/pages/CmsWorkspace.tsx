import { useState, useEffect } from "react";
import {
  Container,
  Tabs,
  Title,
  Text,
  Badge,
  Card,
  Group,
  Stack,
  Button,
  TextInput,
  Textarea,
  Select,
  Switch,
  Modal,
  Table,
  SimpleGrid,
  Timeline,
  Paper,
  Alert,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaListAlt,
  FaTools,
  FaExclamationTriangle,
  FaBullhorn,
  FaChartPie,
  FaUserShield,
  FaPlus,
  FaCheck,
  FaSync,
  FaRedo,
} from "react-icons/fa";

import { http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

export interface Complaint {
  id: number;
  complaint_id: string;
  complainant_user_id: number;
  category: string;
  description: string;
  priority: string;
  status: string;
  assigned_handler_id?: number | null;
  resolution_details?: string;
  rejection_reason?: string;
  requires_supervisor_verification: boolean;
  user_verified: boolean;
  supervisor_verified: boolean;
  closure_timestamp?: string | null;
  is_escalated: boolean;
  escalation_type: string;
  escalation_remarks?: string;
  sla_due_date?: string | null;
  submission_timestamp: string;
  progress_history?: Array<{
    id: number;
    actor_user_id: number;
    actor_role: string;
    action: string;
    remarks: string;
    timestamp: string;
  }>;
  reopenings?: Array<{
    id: number;
    complainant_user_id: number;
    dissatisfaction_reason: string;
    status: string;
    supervisor_remarks?: string;
    requested_at: string;
  }>;
}

export interface Announcement {
  id: number;
  title: string;
  content: string;
  author_role: string;
  published_at: string;
  is_active: boolean;
}

export interface RoleAssignment {
  id: number;
  user_id: number;
  role_type: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

export interface ReportsData {
  total: number;
  total_complaints: number;
  submitted: number;
  in_progress: number;
  resolved: number;
  rejected: number;
  closed: number;
  escalated: number;
  average_rating: number;
  by_category: Record<string, number>;
}

export default function CmsWorkspace({ defaultTab = "my_complaints" }: { defaultTab?: string }) {
  const [activeTab, setActiveTab] = useState<string | null>(defaultTab);
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [roles, setRoles] = useState<RoleAssignment[]>([]);
  const [reports, setReports] = useState<ReportsData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  // Modals state
  const [newComplaintModal, setNewComplaintModal] = useState(false);
  const [newAnnouncementModal, setNewAnnouncementModal] = useState(false);
  const [assignModal, setAssignModal] = useState(false);
  const [progressModal, setProgressModal] = useState(false);
  const [resolveModal, setResolveModal] = useState(false);
  const [rejectModal, setRejectModal] = useState(false);
  const [reopenModal, setReopenModal] = useState(false);
  const [selectedComplaint, setSelectedComplaint] = useState<Complaint | null>(null);

  // Form states
  const [category, setCategory] = useState<string>("hostel");
  const [description, setDescription] = useState<string>("");
  const [priority, setPriority] = useState<string>("Low");
  const [reqSupervisor, setReqSupervisor] = useState<boolean>(false);

  const [assignHandlerId, setAssignHandlerId] = useState<string>("5001");
  const [assignPriority, setAssignPriority] = useState<string>("Medium");

  const [progressRemarks, setProgressRemarks] = useState<string>("");
  const [progressAction, setProgressAction] = useState<string>("WORK_IN_PROGRESS");

  const [resolutionDetails, setResolutionDetails] = useState<string>("");
  const [rejectionReason, setRejectionReason] = useState<string>("");
  const [reopenReason, setReopenReason] = useState<string>("");

  const [annTitle, setAnnTitle] = useState<string>("");
  const [annContent, setAnnContent] = useState<string>("");

  const loadData = async () => {
    setLoading(true);
    try {
      const [cRes, aRes, rRes, repRes] = await Promise.all([
        http.get<Complaint[]>("/cms/complaints/"),
        http.get<Announcement[]>("/cms/announcements/"),
        http.get<RoleAssignment[]>("/cms/roles/"),
        http.get<ReportsData>("/cms/complaints/reports/"),
      ]);
      setComplaints(Array.isArray(cRes.data) ? cRes.data : ((cRes.data as any)?.results ?? []));
      setAnnouncements(Array.isArray(aRes.data) ? aRes.data : ((aRes.data as any)?.results ?? []));
      setRoles(Array.isArray(rRes.data) ? rRes.data : ((rRes.data as any)?.results ?? []));
      setReports(repRes.data);
    } catch (err: any) {
      notifications.show({
        title: "Connection Alert",
        message: err.message || "Failed to synchronize with CMS backend.",
        color: "yellow",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateComplaint = async () => {
    if (!description.trim()) {
      notifications.show({ title: "Validation Error", message: "Description is mandatory.", color: "red" });
      return;
    }
    try {
      await http.post("/cms/complaints/", {
        category,
        description,
        priority,
        requires_supervisor_verification: reqSupervisor,
      });
      notifications.show({ title: "Success", message: "Complaint submitted successfully.", color: "green" });
      setNewComplaintModal(false);
      setDescription("");
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Submission Failed", message: err.message || "Request failed.", color: "red" });
    }
  };

  const handleAssign = async () => {
    if (!selectedComplaint) return;
    try {
      await http.post(`/cms/complaints/${selectedComplaint.id}/assign/`, {
        handler_id: parseInt(assignHandlerId, 10),
        priority: assignPriority,
      });
      notifications.show({ title: "Assigned", message: `Handler assigned with priority ${assignPriority}.`, color: "green" });
      setAssignModal(false);
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Assignment Failed", message: err.message, color: "red" });
    }
  };

  const handleProgress = async () => {
    if (!selectedComplaint || !progressRemarks.trim()) return;
    try {
      await http.post(`/cms/complaints/${selectedComplaint.id}/update_progress/`, {
        remarks: progressRemarks,
        action: progressAction,
      });
      notifications.show({ title: "Updated", message: "Progress recorded.", color: "green" });
      setProgressModal(false);
      setProgressRemarks("");
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Update Failed", message: err.message, color: "red" });
    }
  };

  const handleResolve = async () => {
    if (!selectedComplaint || !resolutionDetails.trim()) return;
    try {
      await http.post(`/cms/complaints/${selectedComplaint.id}/resolve/`, {
        resolution_details: resolutionDetails,
      });
      notifications.show({ title: "Resolved", message: "Complaint marked resolved.", color: "green" });
      setResolveModal(false);
      setResolutionDetails("");
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Action Failed", message: err.message, color: "red" });
    }
  };

  const handleReject = async () => {
    if (!selectedComplaint || !rejectionReason.trim()) return;
    try {
      await http.post(`/cms/complaints/${selectedComplaint.id}/reject/`, {
        rejection_reason: rejectionReason,
      });
      notifications.show({ title: "Rejected", message: "Complaint rejected with reason.", color: "orange" });
      setRejectModal(false);
      setRejectionReason("");
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Action Failed", message: err.message, color: "red" });
    }
  };

  const handleVerifyClosure = async (complaintId: number) => {
    try {
      await http.post(`/cms/complaints/${complaintId}/verify_closure/`, {
        user_satisfied: true,
        remarks: "User verified closure.",
      });
      notifications.show({ title: "Verified", message: "Closure confirmed.", color: "green" });
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Verification Failed", message: err.message, color: "red" });
    }
  };

  const handleReopenRequest = async () => {
    if (!selectedComplaint || !reopenReason.trim()) return;
    try {
      await http.post(`/cms/complaints/${selectedComplaint.id}/request_reopen/`, {
        dissatisfaction_reason: reopenReason,
      });
      notifications.show({ title: "Requested", message: "Reopening request registered for supervisor review.", color: "blue" });
      setReopenModal(false);
      setReopenReason("");
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Reopening Failed", message: err.message, color: "red" });
    }
  };

  const handleTriggerSlaAudit = async () => {
    try {
      const res = await http.post("/cms/complaints/check_sla/");
      notifications.show({
        title: "Autonomous SLA Sweep",
        message: `Sweep finished: ${res.data.escalations_triggered} escalated, ${res.data.reminders_sent} notified.`,
        color: "blue",
      });
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Sweep Failed", message: err.message, color: "red" });
    }
  };

  const handleCreateAnnouncement = async () => {
    if (!annTitle.trim() || !annContent.trim()) return;
    try {
      await http.post("/cms/announcements/", {
        title: annTitle,
        content: annContent,
        author_role: "complaint_supervisor",
      });
      notifications.show({ title: "Published", message: "Broadcast announcement live.", color: "green" });
      setNewAnnouncementModal(false);
      setAnnTitle("");
      setAnnContent("");
      loadData();
    } catch (err: any) {
      notifications.show({ title: "Publish Failed", message: err.message, color: "red" });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "Submitted":
        return "blue";
      case "In Progress":
        return "yellow";
      case "Resolved":
        return "teal";
      case "Closed":
        return "green";
      case "Rejected":
        return "gray";
      default:
        return "indigo";
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "High":
        return "red";
      case "Medium":
        return "orange";
      default:
        return "blue";
    }
  };

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Complaint Management System (CMS)"
        subtitle="End-to-end incident lifecycle: triage, SLA governance, escalation matrix, and resolution audit"
        action={
          <Group>
            <Button variant="light" leftSection={<FaSync />} onClick={loadData} loading={loading}>
              Refresh
            </Button>
            <Button leftSection={<FaPlus />} onClick={() => setNewComplaintModal(true)}>
              Lodge Complaint
            </Button>
          </Group>
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab} mt="md">
        <Tabs.List>
          <Tabs.Tab value="my_complaints" leftSection={<FaListAlt />}>
            My Complaints
          </Tabs.Tab>
          <Tabs.Tab value="handler" leftSection={<FaTools />}>
            Handler Queue
          </Tabs.Tab>
          <Tabs.Tab value="escalations" leftSection={<FaExclamationTriangle />}>
            Supervisor Escalations
          </Tabs.Tab>
          <Tabs.Tab value="announcements" leftSection={<FaBullhorn />}>
            Announcements ({announcements.length})
          </Tabs.Tab>
          <Tabs.Tab value="reports" leftSection={<FaChartPie />}>
            Analytics & SLAs
          </Tabs.Tab>
          <Tabs.Tab value="roles" leftSection={<FaUserShield />}>
            Role Governance
          </Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: My Complaints */}
        <Tabs.Panel value="my_complaints" pt="md">
          {complaints.length === 0 ? (
            <Paper p="xl" withBorder style={{ textAlign: "center" }}>
              <Text c="dimmed">No complaints filed yet. Click "Lodge Complaint" to register one.</Text>
            </Paper>
          ) : (
            <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
              {complaints.map((c) => (
                <Card key={c.id} shadow="sm" padding="lg" radius="md" withBorder>
                  <Group justify="space-between" mb="xs">
                    <Group>
                      <Text fw={700} size="md">
                        {c.complaint_id}
                      </Text>
                      <Badge color={getStatusColor(c.status)} variant="filled">
                        {c.status}
                      </Badge>
                      {c.is_escalated && (
                        <Badge color="red" variant="dot">
                          Escalated ({c.escalation_type})
                        </Badge>
                      )}
                    </Group>
                    <Badge color={getPriorityColor(c.priority)} variant="light">
                      {c.priority} Priority
                    </Badge>
                  </Group>

                  <Text size="sm" c="dimmed" mb="xs">
                    Category: <b>{c.category.toUpperCase()}</b> • Submitted:{" "}
                    {new Date(c.submission_timestamp).toLocaleString()}
                  </Text>

                  <Text size="sm" mb="md">
                    {c.description}
                  </Text>

                  {c.resolution_details && (
                    <Alert title="Resolution Notes" color="teal" mb="sm">
                      {c.resolution_details}
                    </Alert>
                  )}

                  {c.rejection_reason && (
                    <Alert title="Rejection Reason" color="red" mb="sm">
                      {c.rejection_reason}
                    </Alert>
                  )}

                  {c.progress_history && c.progress_history.length > 0 && (
                    <Timeline active={c.progress_history.length - 1} bulletSize={18} lineWidth={2} mb="md">
                      {c.progress_history.map((p) => (
                        <Timeline.Item key={p.id} title={p.action.replace("_", " ").toUpperCase()}>
                          <Text size="xs" c="dimmed">
                            {p.actor_role} • {new Date(p.timestamp).toLocaleTimeString()}
                          </Text>
                          <Text size="xs">{p.remarks}</Text>
                        </Timeline.Item>
                      ))}
                    </Timeline>
                  )}

                  <Group mt="auto" justify="flex-end">
                    {c.status === "Resolved" && (
                      <Button
                        size="xs"
                        color="teal"
                        leftSection={<FaCheck />}
                        onClick={() => handleVerifyClosure(c.id)}
                      >
                        Verify & Close
                      </Button>
                    )}
                    {c.status === "Closed" && (
                      <Button
                        size="xs"
                        variant="light"
                        color="orange"
                        leftSection={<FaRedo />}
                        onClick={() => {
                          setSelectedComplaint(c);
                          setReopenModal(true);
                        }}
                      >
                        Request Reopen
                      </Button>
                    )}
                  </Group>
                </Card>
              ))}
            </SimpleGrid>
          )}
        </Tabs.Panel>

        {/* Tab 2: Handler Queue */}
        <Tabs.Panel value="handler" pt="md">
          <Table striped highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Complaint ID</Table.Th>
                <Table.Th>Category</Table.Th>
                <Table.Th>Priority</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Assigned Handler</Table.Th>
                <Table.Th>SLA Due Date</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {complaints.map((c) => (
                <Table.Tr key={c.id}>
                  <Table.Td fw={600}>{c.complaint_id}</Table.Td>
                  <Table.Td>{c.category}</Table.Td>
                  <Table.Td>
                    <Badge color={getPriorityColor(c.priority)}>{c.priority}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge color={getStatusColor(c.status)}>{c.status}</Badge>
                  </Table.Td>
                  <Table.Td>{c.assigned_handler_id ? `User #${c.assigned_handler_id}` : "Unassigned"}</Table.Td>
                  <Table.Td>
                    {c.sla_due_date ? new Date(c.sla_due_date).toLocaleDateString() : "—"}
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button
                        size="compact-xs"
                        variant="light"
                        onClick={() => {
                          setSelectedComplaint(c);
                          setAssignModal(true);
                        }}
                      >
                        Assign
                      </Button>
                      <Button
                        size="compact-xs"
                        variant="subtle"
                        onClick={() => {
                          setSelectedComplaint(c);
                          setProgressModal(true);
                        }}
                      >
                        Progress
                      </Button>
                      <Button
                        size="compact-xs"
                        color="teal"
                        onClick={() => {
                          setSelectedComplaint(c);
                          setResolveModal(true);
                        }}
                      >
                        Resolve
                      </Button>
                      <Button
                        size="compact-xs"
                        color="red"
                        variant="light"
                        onClick={() => {
                          setSelectedComplaint(c);
                          setRejectModal(true);
                        }}
                      >
                        Reject
                      </Button>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Tabs.Panel>

        {/* Tab 3: Supervisor Escalations */}
        <Tabs.Panel value="escalations" pt="md">
          <Group justify="space-between" mb="md">
            <Text size="sm" c="dimmed">
              Showing critical breaches, manual escalations, and adjudication workflows.
            </Text>
            <Button
              leftSection={<FaTools />}
              color="indigo"
              variant="outline"
              size="xs"
              onClick={handleTriggerSlaAudit}
            >
              Run Autonomous SLA Audit Sweep
            </Button>
          </Group>

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            {complaints
              .filter((c) => c.is_escalated)
              .map((c) => (
                <Card key={c.id} shadow="sm" padding="lg" radius="md" withBorder>
                  <Group justify="space-between" mb="xs">
                    <Text fw={700}>{c.complaint_id}</Text>
                    <Badge color="red" variant="filled">
                      {c.escalation_type.toUpperCase()} BREACH
                    </Badge>
                  </Group>
                  <Text size="sm" mb="xs">
                    <b>Remarks:</b> {c.escalation_remarks || "SLA Deadline expired without resolution."}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Due Date: {c.sla_due_date ? new Date(c.sla_due_date).toLocaleString() : "N/A"}
                  </Text>
                </Card>
              ))}
          </SimpleGrid>
        </Tabs.Panel>

        {/* Tab 4: Announcements */}
        <Tabs.Panel value="announcements" pt="md">
          <Group justify="flex-end" mb="md">
            <Button
              size="xs"
              leftSection={<FaBullhorn />}
              onClick={() => setNewAnnouncementModal(true)}
            >
              Post Campus Announcement
            </Button>
          </Group>
          <Stack gap="md">
            {announcements.map((a) => (
              <Card key={a.id} shadow="xs" padding="md" radius="sm" withBorder>
                <Group justify="space-between" mb="xs">
                  <Text fw={600} size="md">
                    {a.title}
                  </Text>
                  <Badge color="blue" size="xs">
                    {new Date(a.published_at).toLocaleDateString()}
                  </Badge>
                </Group>
                <Text size="sm">{a.content}</Text>
              </Card>
            ))}
          </Stack>
        </Tabs.Panel>

        {/* Tab 5: Analytics & Reports */}
        <Tabs.Panel value="reports" pt="md">
          {reports && (
            <Stack gap="lg">
              <SimpleGrid cols={{ base: 2, md: 5 }}>
                <Paper withBorder p="md" radius="md" style={{ textAlign: "center" }}>
                  <Text size="xs" c="dimmed">Total Incidents</Text>
                  <Title order={3}>{reports.total_complaints}</Title>
                </Paper>
                <Paper withBorder p="md" radius="md" style={{ textAlign: "center" }}>
                  <Text size="xs" c="dimmed">In Progress</Text>
                  <Title order={3} c="yellow">{reports.in_progress}</Title>
                </Paper>
                <Paper withBorder p="md" radius="md" style={{ textAlign: "center" }}>
                  <Text size="xs" c="dimmed">Resolved & Closed</Text>
                  <Title order={3} c="teal">{reports.resolved + reports.closed}</Title>
                </Paper>
                <Paper withBorder p="md" radius="md" style={{ textAlign: "center" }}>
                  <Text size="xs" c="dimmed">Escalated</Text>
                  <Title order={3} c="red">{reports.escalated}</Title>
                </Paper>
                <Paper withBorder p="md" radius="md" style={{ textAlign: "center" }}>
                  <Text size="xs" c="dimmed">User Rating</Text>
                  <Title order={3} c="blue">{reports.average_rating} / 5</Title>
                </Paper>
              </SimpleGrid>

              <Card withBorder p="md">
                <Title order={4} mb="sm">Category Breakdown</Title>
                <SimpleGrid cols={{ base: 2, md: 3 }}>
                  {Object.entries(reports.by_category || {}).map(([cat, count]) => (
                    <Group key={cat} justify="space-between" p="xs" style={{ borderBottom: "1px solid #eee" }}>
                      <Text size="sm" tt="capitalize">{cat}</Text>
                      <Badge variant="light">{count}</Badge>
                    </Group>
                  ))}
                </SimpleGrid>
              </Card>
            </Stack>
          )}
        </Tabs.Panel>

        {/* Tab 6: Role Governance */}
        <Tabs.Panel value="roles" pt="md">
          <Table withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>User ID</Table.Th>
                <Table.Th>Role Type</Table.Th>
                <Table.Th>Start Date</Table.Th>
                <Table.Th>End Date</Table.Th>
                <Table.Th>Status</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {roles.map((r) => (
                <Table.Tr key={r.id}>
                  <Table.Td>User #{r.user_id}</Table.Td>
                  <Table.Td>
                    <Badge color="violet">{r.role_type}</Badge>
                  </Table.Td>
                  <Table.Td>{r.start_date}</Table.Td>
                  <Table.Td>{r.end_date}</Table.Td>
                  <Table.Td>
                    <Badge color={r.is_active ? "green" : "gray"}>
                      {r.is_active ? "Active" : "Archived"}
                    </Badge>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Tabs.Panel>
      </Tabs>

      {/* Lodge Complaint Modal */}
      <Modal opened={newComplaintModal} onClose={() => setNewComplaintModal(false)} title="Lodge New Incident">
        <Stack>
          <Select
            label="Incident Category"
            value={category}
            onChange={(val) => setCategory(val || "hostel")}
            data={[
              { value: "hostel", label: "Hostel & Living" },
              { value: "academic", label: "Academic & Classrooms" },
              { value: "maintenance", label: "Civil / Maintenance" },
              { value: "network", label: "Campus Network / Wi-Fi" },
              { value: "mess", label: "Dining & Mess" },
              { value: "other", label: "Other Services" },
            ]}
          />
          <Textarea
            label="Incident Description"
            placeholder="Provide clear details and location..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            rows={4}
          />
          <Select
            label="Initial Priority"
            value={priority}
            onChange={(val) => setPriority(val || "Low")}
            data={[
              { value: "Low", label: "Low (7 days SLA)" },
              { value: "Medium", label: "Medium (3 days SLA)" },
              { value: "High", label: "High (24 hours SLA)" },
            ]}
          />
          <Switch
            label="Require Supervisor Closure Sign-off"
            checked={reqSupervisor}
            onChange={(e) => setReqSupervisor(e.currentTarget.checked)}
          />
          <Button fullWidth onClick={handleCreateComplaint}>
            Confirm Submission
          </Button>
        </Stack>
      </Modal>

      {/* Assign Handler Modal */}
      <Modal opened={assignModal} onClose={() => setAssignModal(false)} title="Assign Handler & SLA">
        <Stack>
          <TextInput
            label="Handler User ID"
            value={assignHandlerId}
            onChange={(e) => setAssignHandlerId(e.target.value)}
          />
          <Select
            label="Priority Tier"
            value={assignPriority}
            onChange={(val) => setAssignPriority(val || "Medium")}
            data={[
              { value: "Low", label: "Low (7 days)" },
              { value: "Medium", label: "Medium (3 days)" },
              { value: "High", label: "High (24 hrs)" },
            ]}
          />
          <Button fullWidth onClick={handleAssign}>
            Confirm Assignment
          </Button>
        </Stack>
      </Modal>

      {/* Progress Update Modal */}
      <Modal opened={progressModal} onClose={() => setProgressModal(false)} title="Record Operational Progress">
        <Stack>
          <Select
            label="Progress Stage"
            value={progressAction}
            onChange={(val) => setProgressAction(val || "WORK_IN_PROGRESS")}
            data={[
              { value: "DIAGNOSTIC_COMPLETED", label: "Diagnostics Completed" },
              { value: "PARTS_ORDERED", label: "Spare Parts Ordered" },
              { value: "WORK_IN_PROGRESS", label: "Work Underway" },
            ]}
          />
          <Textarea
            label="Progress Remarks"
            value={progressRemarks}
            onChange={(e) => setProgressRemarks(e.target.value)}
            required
            rows={3}
          />
          <Button fullWidth onClick={handleProgress}>
            Append Progress Record
          </Button>
        </Stack>
      </Modal>

      {/* Resolve Modal */}
      <Modal opened={resolveModal} onClose={() => setResolveModal(false)} title="Mark Incident Resolved">
        <Stack>
          <Textarea
            label="Resolution Details"
            placeholder="Explain root cause and corrective work performed..."
            value={resolutionDetails}
            onChange={(e) => setResolutionDetails(e.target.value)}
            required
            rows={4}
          />
          <Button fullWidth color="teal" onClick={handleResolve}>
            Confirm Resolution
          </Button>
        </Stack>
      </Modal>

      {/* Reject Modal */}
      <Modal opened={rejectModal} onClose={() => setRejectModal(false)} title="Reject Incident">
        <Stack>
          <Textarea
            label="Rejection Reason"
            placeholder="Explain reason for rejection..."
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            required
            rows={3}
          />
          <Button fullWidth color="red" onClick={handleReject}>
            Confirm Rejection
          </Button>
        </Stack>
      </Modal>

      {/* Reopen Modal */}
      <Modal opened={reopenModal} onClose={() => setReopenModal(false)} title="Request Incident Reopening">
        <Stack>
          <Textarea
            label="Reason for Dissatisfaction"
            placeholder="Explain why issue is unresolved..."
            value={reopenReason}
            onChange={(e) => setReopenReason(e.target.value)}
            required
            rows={3}
          />
          <Button fullWidth color="orange" onClick={handleReopenRequest}>
            Submit Reopen Request
          </Button>
        </Stack>
      </Modal>

      {/* Announcement Modal */}
      <Modal opened={newAnnouncementModal} onClose={() => setNewAnnouncementModal(false)} title="Broadcast Announcement">
        <Stack>
          <TextInput
            label="Announcement Title"
            value={annTitle}
            onChange={(e) => setAnnTitle(e.target.value)}
            required
          />
          <Textarea
            label="Broadcast Content"
            value={annContent}
            onChange={(e) => setAnnContent(e.target.value)}
            required
            rows={4}
          />
          <Button fullWidth onClick={handleCreateAnnouncement}>
            Broadcast to Campus
          </Button>
        </Stack>
      </Modal>
    </Container>
  );
}
