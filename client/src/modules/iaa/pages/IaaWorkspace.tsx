import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Modal,
  Progress,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaCheck,
  FaFileInvoiceDollar,
  FaLock,
  FaMoneyBillWave,
  FaPlaneDeparture,
  FaPlus,
  FaScaleUnbalanced,
  FaShieldHalved,
  FaTriangleExclamation,
} from "react-icons/fa6";

import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useAnomalies,
  useApprovalActions,
  useApproveExpense,
  useApproveTAClaim,
  useAuditObservations,
  useBudgets,
  useCloseAuditObservation,
  useCompleteExpense,
  useCreateAuditObservation,
  useCreateExpense,
  useCreateTAClaim,
  useExpenses,
  useRejectExpense,
  useResolveAnomaly,
  useRespondAuditObservation,
  useSubmitExpense,
  useTAClaims,
} from "../api/hooks";
import type { AuditObservation, ExpenseRequest } from "../api/types";

export default function IaaWorkspace() {
  const [activeTab, setActiveTab] = useState<string | null>("expenses");

  // Data Queries
  const { data: expenses = [] } = useExpenses();
  const { data: taClaims = [] } = useTAClaims();
  const { data: budgets = [] } = useBudgets();
  const { data: anomalies = [] } = useAnomalies();
  const { data: auditObservations = [] } = useAuditObservations();
  const { data: actions = [] } = useApprovalActions();

  // Mutations
  const createExpense = useCreateExpense();
  const submitExpense = useSubmitExpense();
  const approveExpense = useApproveExpense();
  const rejectExpense = useRejectExpense();
  const completeExpense = useCompleteExpense();

  const createTA = useCreateTAClaim();
  const approveTA = useApproveTAClaim();

  const resolveAnomaly = useResolveAnomaly();
  const createAudit = useCreateAuditObservation();
  const respondAudit = useRespondAuditObservation();
  const closeAudit = useCloseAuditObservation();

  // Modals state
  const [expenseModalOpen, setExpenseModalOpen] = useState(false);
  const [newExpense, setNewExpense] = useState({
    title: "",
    description: "",
    department: "CSE",
    amount: "10000",
    creator_user_id: "user123",
    creator_role: "faculty",
  });

  const [taModalOpen, setTAModalOpen] = useState(false);
  const [newTA, setNewTA] = useState({
    purpose: "",
    departure_location: "Jabalpur",
    destination_location: "Delhi",
    travel_start_date: "2026-11-10",
    travel_end_date: "2026-11-15",
    total_amount: "15000",
    claimant_user_id: "user123",
    claimant_role: "faculty",
  });

  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState<ExpenseRequest | null>(null);
  const [actionType, setActionType] = useState<"approve" | "reject">("approve");
  const [actorUserId, setActorUserId] = useState("hod_cse");
  const [actorRole, setActorRole] = useState("hod");
  const [actionRemarks, setActionRemarks] = useState("");

  const [auditModalOpen, setAuditModalOpen] = useState(false);
  const [newAudit, setNewAudit] = useState({
    observation_title: "",
    observation_details: "",
    department: "CSE",
    auditor_user_id: "auditor01",
  });

  const [auditRespModalOpen, setAuditRespModalOpen] = useState(false);
  const [selectedAudit, setSelectedAudit] = useState<AuditObservation | null>(null);
  const [auditResponseText, setAuditResponseText] = useState("");

  // Handlers
  const handleCreateExpense = async () => {
    try {
      await createExpense.mutateAsync(newExpense);
      notifications.show({
        title: "Expense Created",
        message: "New draft expense request created successfully.",
        color: "green",
      });
      setExpenseModalOpen(false);
      setNewExpense({ title: "", description: "", department: "CSE", amount: "10000", creator_user_id: "user123", creator_role: "faculty" });
    } catch (err: any) {
      notifications.show({
        title: "Creation Failed",
        message: err?.response?.data?.error || "Failed to create expense request",
        color: "red",
      });
    }
  };

  const handleSubmitExpense = async (id: number) => {
    try {
      await submitExpense.mutateAsync(id);
      notifications.show({
        title: "Submitted",
        message: "Request submitted and locked for review (IAA-BR-104).",
        color: "blue",
      });
    } catch (err: any) {
      notifications.show({
        title: "Submission Error",
        message: err?.response?.data?.error || "Submission failed",
        color: "red",
      });
    }
  };

  const handleExecuteExpenseAction = async () => {
    if (!selectedExpense) return;
    if (!actionRemarks.trim()) {
      notifications.show({
        title: "Validation Error",
        message: "Remarks are mandatory for approval or rejection (IAA-BR-005).",
        color: "red",
      });
      return;
    }

    try {
      if (actionType === "approve") {
        await approveExpense.mutateAsync({
          id: selectedExpense.id,
          actor_user_id: actorUserId,
          actor_role: actorRole,
          remarks: actionRemarks,
        });
        notifications.show({
          title: "Approved",
          message: "Request approved and routed to next tier or finalized.",
          color: "green",
        });
      } else {
        await rejectExpense.mutateAsync({
          id: selectedExpense.id,
          actor_user_id: actorUserId,
          actor_role: actorRole,
          remarks: actionRemarks,
        });
        notifications.show({
          title: "Rejected",
          message: "Request has been rejected with mandatory remarks.",
          color: "orange",
        });
      }
      setActionModalOpen(false);
      setActionRemarks("");
    } catch (err: any) {
      const msg = err?.response?.data?.error || "Action could not be executed.";
      notifications.show({
        title: "Action Prohibited (Segregation of Duties)",
        message: msg,
        color: "red",
      });
    }
  };

  const handleCompleteExpense = async (id: number) => {
    try {
      await completeExpense.mutateAsync(id);
      notifications.show({
        title: "Internal Non-Monetary Completion",
        message: "Request marked complete; department spent budget updated (IAA-BR-006).",
        color: "green",
      });
    } catch (err: any) {
      notifications.show({
        title: "Completion Error",
        message: err?.response?.data?.error || "Failed to complete request.",
        color: "red",
      });
    }
  };

  const handleCreateTA = async () => {
    try {
      await createTA.mutateAsync(newTA);
      notifications.show({
        title: "TA Claim Created",
        message: "Travel allowance claim filed successfully.",
        color: "green",
      });
      setTAModalOpen(false);
      setNewTA({
        purpose: "",
        departure_location: "Jabalpur",
        destination_location: "Delhi",
        travel_start_date: "2026-11-10",
        travel_end_date: "2026-11-15",
        total_amount: "15000",
        claimant_user_id: "user123",
        claimant_role: "faculty",
      });
    } catch (err: any) {
      notifications.show({
        title: "TA Creation Failed",
        message: err?.response?.data?.error || "Failed to submit TA claim.",
        color: "red",
      });
    }
  };

  const handleCreateAudit = async () => {
    try {
      await createAudit.mutateAsync(newAudit);
      notifications.show({
        title: "Audit Observation Issued",
        message: "Observation published to department for response (IAA-BR-301).",
        color: "green",
      });
      setAuditModalOpen(false);
      setNewAudit({ observation_title: "", observation_details: "", department: "CSE", auditor_user_id: "auditor01" });
    } catch (err: any) {
      notifications.show({
        title: "Audit Creation Failed",
        message: err?.response?.data?.error || "Failed to issue observation.",
        color: "red",
      });
    }
  };

  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Institute Accounts and Audits (IAA)"
        subtitle="Financial governance, approval hierarchy, non-monetary ledger management, and audit tracking"
        action={
          <Group>
            <Button
              leftSection={<FaPlus size={14} />}
              onClick={() => setExpenseModalOpen(true)}
              color="blue"
            >
              New Expense Request
            </Button>
            <Button
              leftSection={<FaPlaneDeparture size={14} />}
              onClick={() => setTAModalOpen(true)}
              variant="light"
              color="indigo"
            >
              File TA Claim
            </Button>
          </Group>
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab} variant="outline" radius="md">
        <Tabs.List mb="md">
          <Tabs.Tab value="expenses" leftSection={<FaFileInvoiceDollar size={16} />}>
            Expense Requests ({expenses.length})
          </Tabs.Tab>
          <Tabs.Tab value="ta" leftSection={<FaPlaneDeparture size={16} />}>
            TA Claims ({taClaims.length})
          </Tabs.Tab>
          <Tabs.Tab value="budgets" leftSection={<FaMoneyBillWave size={16} />}>
            Department Budgets ({budgets.length})
          </Tabs.Tab>
          <Tabs.Tab value="anomalies" leftSection={<FaTriangleExclamation size={16} />}>
            Anomalies ({anomalies.filter((a) => a.status === "open").length})
          </Tabs.Tab>
          <Tabs.Tab value="audit" leftSection={<FaShieldHalved size={16} />}>
            Audit Observations ({auditObservations.length})
          </Tabs.Tab>
          <Tabs.Tab value="actions" leftSection={<FaScaleUnbalanced size={16} />}>
            Audit Trail ({actions.length})
          </Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: Expense Requests */}
        <Tabs.Panel value="expenses">
          <Card withBorder radius="md" p="md">
            <Group justify="space-between" mb="sm">
              <Title order={4}>Institutional Expense Requests</Title>
              <Text size="sm" c="dimmed">
                Hierarchical routing: HOD (≤ ₹50k) → Dean (≤ ₹200k) → Director (&gt; ₹200k)
              </Text>
            </Group>

            {expenses.length === 0 ? (
              <Text c="dimmed" py="xl" ta="center">
                No expense requests found. Click "New Expense Request" to create one.
              </Text>
            ) : (
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Title & Dept</Table.Th>
                    <Table.Th>Amount (₹)</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Assigned Role</Table.Th>
                    <Table.Th>Locked</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {expenses.map((exp) => (
                    <Table.Tr key={exp.id}>
                      <Table.Td fw={600}>EXP-{exp.id}</Table.Td>
                      <Table.Td>
                        <Text fw={500}>{exp.title}</Text>
                        <Text size="xs" c="dimmed">
                          Dept: {exp.department} | Creator: {exp.creator_user_id} ({exp.creator_role})
                        </Text>
                      </Table.Td>
                      <Table.Td fw={600}>₹{parseFloat(exp.amount).toLocaleString()}</Table.Td>
                      <Table.Td>
                        <StatusBadge status={exp.status} />
                      </Table.Td>
                      <Table.Td>
                        <Badge variant="outline" color="cyan" size="sm">
                          {exp.current_authority_role || "none"}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        {exp.is_locked ? (
                          <Badge color="red" variant="dot" size="sm" leftSection={<FaLock size={10} />}>
                            Locked
                          </Badge>
                        ) : (
                          <Badge color="green" variant="dot" size="sm">
                            Editable
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <Group gap={6}>
                          {exp.status === "draft" && (
                            <Button size="xs" variant="light" color="blue" onClick={() => handleSubmitExpense(exp.id)}>
                              Submit
                            </Button>
                          )}
                          {exp.status === "under_review" && (
                            <Button
                              size="xs"
                              color="green"
                              onClick={() => {
                                setSelectedExpense(exp);
                                setActionType("approve");
                                setActionModalOpen(true);
                              }}
                            >
                              Review
                            </Button>
                          )}
                          {exp.status === "approved" && (
                            <Button size="xs" color="teal" onClick={() => handleCompleteExpense(exp.id)}>
                              Complete (IAA-BR-006)
                            </Button>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>

        {/* Tab 2: TA Claims */}
        <Tabs.Panel value="ta">
          <Card withBorder radius="md" p="md">
            <Group justify="space-between" mb="sm">
              <Title order={4}>Travel Allowance (TA) Claims</Title>
              <Text size="sm" c="dimmed">
                High-Value Flag automatically triggered at ≥ ₹50,000 (IAA-BR-202)
              </Text>
            </Group>

            {taClaims.length === 0 ? (
              <Text c="dimmed" py="xl" ta="center">
                No TA claims recorded yet.
              </Text>
            ) : (
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Claimant</Table.Th>
                    <Table.Th>Route & Dates</Table.Th>
                    <Table.Th>Amount (₹)</Table.Th>
                    <Table.Th>Type</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {taClaims.map((claim) => (
                    <Table.Tr key={claim.id}>
                      <Table.Td fw={600}>TA-{claim.id}</Table.Td>
                      <Table.Td>
                        <Text fw={500}>{claim.claimant_user_id}</Text>
                        <Text size="xs" c="dimmed">{claim.claimant_role}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="sm">{claim.departure_location} → {claim.destination_location}</Text>
                        <Text size="xs" c="dimmed">
                          {claim.travel_start_date} to {claim.travel_end_date}
                        </Text>
                      </Table.Td>
                      <Table.Td fw={600}>₹{parseFloat(claim.total_amount).toLocaleString()}</Table.Td>
                      <Table.Td>
                        {claim.is_high_value ? (
                          <Badge color="red" variant="filled" size="sm">
                            High-Value (≥50k)
                          </Badge>
                        ) : (
                          <Badge color="blue" variant="light" size="sm">
                            Standard
                          </Badge>
                        )}
                      </Table.Td>
                      <Table.Td>
                        <StatusBadge status={claim.status} />
                      </Table.Td>
                      <Table.Td>
                        {claim.status === "under_review" && (
                          <Button
                            size="xs"
                            color="green"
                            onClick={async () => {
                              await approveTA.mutateAsync({ id: claim.id, remarks: "TA claim verified and approved." });
                              notifications.show({ title: "Approved", message: "TA Claim approved.", color: "green" });
                            }}
                          >
                            Approve
                          </Button>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>

        {/* Tab 3: Budgets */}
        <Tabs.Panel value="budgets">
          <Card withBorder radius="md" p="md">
            <Title order={4} mb="md">Departmental Budgetary Balances</Title>
            <Grid>
              {budgets.map((b) => {
                const allocated = parseFloat(b.allocated_budget) || 1;
                const committed = parseFloat(b.committed_budget) || 0;
                const spent = parseFloat(b.spent_budget) || 0;
                const available = parseFloat(b.available_budget ?? (allocated - committed - spent).toString());
                const spentPct = Math.min(100, (spent / allocated) * 100);
                const committedPct = Math.min(100, (committed / allocated) * 100);

                return (
                  <Grid.Col span={{ base: 12, md: 6 }} key={b.id}>
                    <Card withBorder padding="lg" radius="md">
                      <Group justify="space-between" mb="xs">
                        <Title order={5}>{b.department} Department</Title>
                        <Badge color="blue">FY {b.fiscal_year}</Badge>
                      </Group>
                      <Text size="sm" c="dimmed" mb="md">
                        Allocated: ₹{allocated.toLocaleString()}
                      </Text>

                      <Group justify="space-between" mb={4}>
                        <Text size="xs">Committed: ₹{committed.toLocaleString()}</Text>
                        <Text size="xs">Spent: ₹{spent.toLocaleString()}</Text>
                      </Group>
                      <Progress.Root size="xl" radius="xl" mb="md">
                        <Progress.Section value={spentPct} color="red" />
                        <Progress.Section value={committedPct} color="orange" />
                      </Progress.Root>

                      <Group justify="space-between" align="center">
                        <Text size="sm" fw={600}>Available Budget:</Text>
                        <Badge size="lg" color={available > 0 ? "teal" : "red"}>
                          ₹{available.toLocaleString()}
                        </Badge>
                      </Group>
                    </Card>
                  </Grid.Col>
                );
              })}
            </Grid>
          </Card>
        </Tabs.Panel>

        {/* Tab 4: Anomalies */}
        <Tabs.Panel value="anomalies">
          <Card withBorder radius="md" p="md">
            <Group justify="space-between" mb="sm">
              <Title order={4}>Financial & Workflow Anomalies</Title>
              <Text size="sm" c="dimmed">
                Automated detection triggered by budget overrun or segregation anomalies (IAA-BR-103)
              </Text>
            </Group>

            {anomalies.length === 0 ? (
              <Alert icon={<FaCheck size={16} />} title="All Clear" color="green" radius="md">
                No active financial or process anomalies detected across departments.
              </Alert>
            ) : (
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Dept</Table.Th>
                    <Table.Th>Description</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {anomalies.map((anom) => (
                    <Table.Tr key={anom.id}>
                      <Table.Td fw={600}>ANM-{anom.id}</Table.Td>
                      <Table.Td>
                        <Badge color="orange" variant="light">
                          {anom.category.replace(/_/g, " ")}
                        </Badge>
                      </Table.Td>
                      <Table.Td fw={500}>{anom.department}</Table.Td>
                      <Table.Td>{anom.description}</Table.Td>
                      <Table.Td>
                        <Badge color={anom.status === "open" ? "red" : "green"}>{anom.status}</Badge>
                      </Table.Td>
                      <Table.Td>
                        {anom.status === "open" && (
                          <Group gap={6}>
                            <Button
                              size="xs"
                              color="teal"
                              onClick={async () => {
                                await resolveAnomaly.mutateAsync({
                                  id: anom.id,
                                  resolution: "resolve",
                                  remarks: "Budget reallocation adjusted and anomaly cleared.",
                                });
                                notifications.show({ title: "Resolved", message: "Anomaly marked resolved.", color: "green" });
                              }}
                            >
                              Resolve
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              variant="outline"
                              onClick={async () => {
                                await resolveAnomaly.mutateAsync({
                                  id: anom.id,
                                  resolution: "escalate",
                                  remarks: "Escalated to internal audit committee.",
                                });
                                notifications.show({ title: "Escalated", message: "Anomaly escalated to audit.", color: "red" });
                              }}
                            >
                              Escalate
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
        </Tabs.Panel>

        {/* Tab 5: Audit Observations */}
        <Tabs.Panel value="audit">
          <Card withBorder radius="md" p="md">
            <Group justify="space-between" mb="sm">
              <Title order={4}>Statutory & Internal Audit Observations</Title>
              <Button leftSection={<FaPlus size={14} />} size="xs" onClick={() => setAuditModalOpen(true)}>
                Issue Observation
              </Button>
            </Group>

            {auditObservations.length === 0 ? (
              <Text c="dimmed" py="xl" ta="center">
                No audit observations issued.
              </Text>
            ) : (
              <Table striped highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>ID</Table.Th>
                    <Table.Th>Title & Scope</Table.Th>
                    <Table.Th>Dept</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Dept Response</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {auditObservations.map((obs) => (
                    <Table.Tr key={obs.id}>
                      <Table.Td fw={600}>AUD-{obs.id}</Table.Td>
                      <Table.Td>
                        <Text fw={500}>{obs.observation_title}</Text>
                        <Text size="xs" c="dimmed">{obs.observation_details}</Text>
                      </Table.Td>
                      <Table.Td fw={500}>{obs.department}</Table.Td>
                      <Table.Td>
                        <Badge color={obs.status === "closed" ? "green" : obs.status === "response_submitted" ? "blue" : "red"}>
                          {obs.status.replace(/_/g, " ")}
                        </Badge>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{obs.department_response || "Awaiting response"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Group gap={6}>
                          {obs.status === "issued" && (
                            <Button
                              size="xs"
                              variant="light"
                              color="blue"
                              onClick={() => {
                                setSelectedAudit(obs);
                                setAuditRespModalOpen(true);
                              }}
                            >
                              Respond
                            </Button>
                          )}
                          {obs.status === "response_submitted" && (
                            <Button
                              size="xs"
                              color="teal"
                              onClick={async () => {
                                await closeAudit.mutateAsync({
                                  id: obs.id,
                                  closure_remarks: "Satisfactorily verified by Auditor. Closed.",
                                });
                                notifications.show({ title: "Audit Closed", message: "Audit observation closed.", color: "green" });
                              }}
                            >
                              Close Observation
                            </Button>
                          )}
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>

        {/* Tab 6: Audit Actions Trail */}
        <Tabs.Panel value="actions">
          <Card withBorder radius="md" p="md">
            <Title order={4} mb="sm">Immutable Financial Governance Audit Trail (IAA-BR-503)</Title>
            <Table striped highlightOnHover verticalSpacing="xs">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Timestamp</Table.Th>
                  <Table.Th>Entity Type</Table.Th>
                  <Table.Th>Target ID</Table.Th>
                  <Table.Th>Actor Role</Table.Th>
                  <Table.Th>Action</Table.Th>
                  <Table.Th>Mandatory Remarks</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {actions.map((act) => (
                  <Table.Tr key={act.id}>
                    <Table.Td>
                      <Text size="xs">{new Date(act.timestamp).toLocaleString()}</Text>
                    </Table.Td>
                    <Table.Td fw={500}>{act.request_type}</Table.Td>
                    <Table.Td fw={600}>#{act.request_id}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline" size="sm">{act.actor_role} ({act.actor_user_id})</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Badge color={act.action === "approved" ? "green" : act.action === "rejected" ? "red" : "blue"}>
                        {act.action}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="xs">{act.remarks}</Text>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Modal: New Expense */}
      <Modal opened={expenseModalOpen} onClose={() => setExpenseModalOpen(false)} title="Create Expense Request">
        <Stack gap="sm">
          <TextInput
            label="Title"
            placeholder="e.g. Lab Hardware Procurement"
            required
            value={newExpense.title}
            onChange={(e) => setNewExpense({ ...newExpense, title: e.target.value })}
          />
          <Textarea
            label="Description & Justification"
            placeholder="Purpose of expenditure..."
            required
            value={newExpense.description}
            onChange={(e) => setNewExpense({ ...newExpense, description: e.target.value })}
          />
          <Select
            label="Department"
            data={["CSE", "ECE", "ME", "Design", "Physics", "Mathematics"]}
            value={newExpense.department}
            onChange={(val) => setNewExpense({ ...newExpense, department: val || "CSE" })}
          />
          <TextInput
            label="Amount (₹)"
            type="number"
            required
            value={newExpense.amount}
            onChange={(e) => setNewExpense({ ...newExpense, amount: e.target.value })}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setExpenseModalOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateExpense} loading={createExpense.isPending}>Create Draft</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: New TA Claim */}
      <Modal opened={taModalOpen} onClose={() => setTAModalOpen(false)} title="File Travel Allowance Claim">
        <Stack gap="sm">
          <TextInput
            label="Purpose of Travel"
            placeholder="e.g. Attending IEEE Conference"
            required
            value={newTA.purpose}
            onChange={(e) => setNewTA({ ...newTA, purpose: e.target.value })}
          />
          <Group grow>
            <TextInput
              label="Departure Location"
              value={newTA.departure_location}
              onChange={(e) => setNewTA({ ...newTA, departure_location: e.target.value })}
            />
            <TextInput
              label="Destination Location"
              value={newTA.destination_location}
              onChange={(e) => setNewTA({ ...newTA, destination_location: e.target.value })}
            />
          </Group>
          <Group grow>
            <TextInput
              label="Start Date"
              type="date"
              value={newTA.travel_start_date}
              onChange={(e) => setNewTA({ ...newTA, travel_start_date: e.target.value })}
            />
            <TextInput
              label="End Date"
              type="date"
              value={newTA.travel_end_date}
              onChange={(e) => setNewTA({ ...newTA, travel_end_date: e.target.value })}
            />
          </Group>
          <TextInput
            label="Total Amount Claimed (₹)"
            type="number"
            value={newTA.total_amount}
            onChange={(e) => setNewTA({ ...newTA, total_amount: e.target.value })}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setTAModalOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateTA} loading={createTA.isPending}>File Claim</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Expense Approval/Rejection with Segregation of Duties Check */}
      <Modal
        opened={actionModalOpen}
        onClose={() => setActionModalOpen(false)}
        title={actionType === "approve" ? "Approve Expense Request" : "Reject Expense Request"}
      >
        <Stack gap="sm">
          <Text size="sm">
            Acting on <strong>EXP-{selectedExpense?.id}</strong> (₹{selectedExpense?.amount})
          </Text>
          <Group grow>
            <Select
              label="Acting Role"
              data={["hod", "dean", "director"]}
              value={actorRole}
              onChange={(v) => {
                const role = v || "hod";
                setActorRole(role);
                setActorUserId(`${role}_officer`);
              }}
            />
            <TextInput
              label="User ID"
              value={actorUserId}
              onChange={(e) => setActorUserId(e.target.value)}
            />
          </Group>
          <Textarea
            label="Mandatory Remarks (IAA-BR-005)"
            placeholder="Provide clear rationale for approval or rejection..."
            required
            value={actionRemarks}
            onChange={(e) => setActionRemarks(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setActionModalOpen(false)}>Cancel</Button>
            <Button
              color={actionType === "approve" ? "green" : "red"}
              onClick={handleExecuteExpenseAction}
              loading={approveExpense.isPending || rejectExpense.isPending}
            >
              {actionType === "approve" ? "Confirm Approval" : "Confirm Rejection"}
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Issue Audit Observation */}
      <Modal opened={auditModalOpen} onClose={() => setAuditModalOpen(false)} title="Issue Audit Observation">
        <Stack gap="sm">
          <TextInput
            label="Observation Title"
            required
            value={newAudit.observation_title}
            onChange={(e) => setNewAudit({ ...newAudit, observation_title: e.target.value })}
          />
          <Textarea
            label="Observation Details"
            required
            value={newAudit.observation_details}
            onChange={(e) => setNewAudit({ ...newAudit, observation_details: e.target.value })}
          />
          <Select
            label="Audited Department"
            data={["CSE", "ECE", "ME", "Design", "Physics", "Mathematics"]}
            value={newAudit.department}
            onChange={(v) => setNewAudit({ ...newAudit, department: v || "CSE" })}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setAuditModalOpen(false)}>Cancel</Button>
            <Button onClick={handleCreateAudit} loading={createAudit.isPending}>Issue Observation</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Audit Response */}
      <Modal opened={auditRespModalOpen} onClose={() => setAuditRespModalOpen(false)} title="Submit Department Response">
        <Stack gap="sm">
          <Text size="sm">Responding to Observation: <strong>{selectedAudit?.observation_title}</strong></Text>
          <Textarea
            label="Departmental Response & Supporting Details"
            required
            value={auditResponseText}
            onChange={(e) => setAuditResponseText(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setAuditRespModalOpen(false)}>Cancel</Button>
            <Button
              onClick={async () => {
                if (!selectedAudit) return;
                await respondAudit.mutateAsync({ id: selectedAudit.id, department_response: auditResponseText });
                notifications.show({ title: "Response Submitted", message: "Department response recorded.", color: "blue" });
                setAuditRespModalOpen(false);
                setAuditResponseText("");
              }}
              loading={respondAudit.isPending}
            >
              Submit Response
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
