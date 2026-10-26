import React, { useState, useEffect } from "react";
import {
  Container,
  Card,
  Title,
  Text,
  Tabs,
  Table,
  Badge,
  Button,
  Group,
  Modal,
  Textarea,
  Loader,
  Center,
  Stack,
  Alert,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckSquare, FaUserCheck, FaUserTie, FaCheck, FaTimes, FaThumbsUp, FaThumbsDown } from "react-icons/fa";

interface AppRecord {
  id: number;
  applicant_username: string;
  leave_type_code: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  days_count: string;
  status: string;
  reason: string;
  substitute_username: string | null;
  substitute_status: string;
  unit_head_recommendation: string;
  unit_head_remarks: string | null;
}

export default function LeaveApprovalsPage() {
  const [activeTab, setActiveTab] = useState<string | null>("substitute");
  const [applications, setApplications] = useState<AppRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Decision Modal
  const [decisionModalOpen, setDecisionModalOpen] = useState<boolean>(false);
  const [selectedApp, setSelectedApp] = useState<AppRecord | null>(null);
  const [actionType, setActionType] = useState<string>("");
  const [remarks, setRemarks] = useState<string>("");

  const fetchApps = async (role: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/leave/applications/?role=${role}`);
      if (res.ok) {
        const data = await res.json();
        setApplications(data.results || data);
      }
    } catch {
      notifications.show({ title: "Error", message: "Failed to load approval queue.", color: "red" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab) {
      fetchApps(activeTab);
    }
  }, [activeTab]);

  const handleSubstituteConsent = async (id: number, accept: boolean) => {
    try {
      const res = await fetch(`/api/v1/leave/applications/${id}/substitute_consent/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accept, remarks: accept ? "Accepted substitute duty" : "Declined substitute duty" }),
      });
      if (res.ok) {
        notifications.show({
          title: "Response Recorded",
          message: accept
            ? "Consent recorded; application progressed to Unit Head (BR-EL-015)."
            : "Declined; applicant notified to nominate replacement.",
          color: accept ? "teal" : "orange",
        });
        if (activeTab) fetchApps(activeTab);
      } else {
        const err = await res.json();
        notifications.show({ title: "Error", message: err.error, color: "red" });
      }
    } catch {
      notifications.show({ title: "Error", message: "Network error recording consent.", color: "red" });
    }
  };

  const submitDecision = async () => {
    if (!selectedApp) return;

    let url = "";
    const payload: any = { decision: actionType, remarks };

    if (activeTab === "unit_head") {
      url = `/api/v1/leave/applications/${selectedApp.id}/unit_head_decision/`;
    } else if (activeTab === "higher_sanction") {
      url = `/api/v1/leave/applications/${selectedApp.id}/higher_sanction_decision/`;
    }

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        notifications.show({
          title: "Decision Executed",
          message: `Decision '${actionType}' recorded for Application #${selectedApp.id}.`,
          color: "teal",
        });
        setDecisionModalOpen(false);
        setRemarks("");
        if (activeTab) fetchApps(activeTab);
      } else {
        const err = await res.json();
        notifications.show({ title: "Error", message: err.error, color: "red" });
      }
    } catch {
      notifications.show({ title: "Error", message: "Failed to record decision.", color: "red" });
    }
  };

  return (
    <Container size="xl" py="xl">
      <Card shadow="sm" padding="xl" radius="md" withBorder>
        <Group justify="space-between" mb="lg">
          <div>
            <Title order={2}>Leave Approval & Review Workflows</Title>
            <Text c="dimmed" size="sm">
              Role-dependent review gates: Substitute Consent (BR-EL-015), Unit Head Action (BR-EL-016/017), Higher Sanction (BR-EL-018).
            </Text>
          </div>
          <FaCheckSquare size={28} color="#228be6" />
        </Group>

        <Tabs value={activeTab} onChange={setActiveTab}>
          <Tabs.List>
            <Tabs.Tab value="substitute" leftSection={<FaUserCheck size={14} />}>
              Substitute Requests
            </Tabs.Tab>
            <Tabs.Tab value="unit_head" leftSection={<FaUserTie size={14} />}>
              Unit Head Review
            </Tabs.Tab>
            <Tabs.Tab value="higher_sanction" leftSection={<FaCheckSquare size={14} />}>
              Higher Sanction Review
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="substitute" pt="md">
            <Alert color="blue" mb="md">
              Applications requiring your substitute consent. Approval routing remains gated until consent is given (BR-EL-015).
            </Alert>
            {renderTable(applications, loading, (app) => (
              <Group gap="xs">
                <Button
                  size="xs"
                  color="teal"
                  leftSection={<FaCheck size={10} />}
                  onClick={() => handleSubstituteConsent(app.id, true)}
                >
                  Accept
                </Button>
                <Button
                  size="xs"
                  color="red"
                  variant="light"
                  leftSection={<FaTimes size={10} />}
                  onClick={() => handleSubstituteConsent(app.id, false)}
                >
                  Decline
                </Button>
              </Group>
            ))}
          </Tabs.Panel>

          <Tabs.Panel value="unit_head" pt="md">
            <Alert color="indigo" mb="md">
              Department Unit Head scope: CL/RH have final approve/reject authority (BR-EL-016). SCL, EL, COL, VL require recommendation and route forward (BR-EL-017).
            </Alert>
            {renderTable(applications, loading, (app) => {
              const isDirectFinal = ["CL", "RH"].includes(app.leave_type_code);
              return (
                <Group gap="xs">
                  {isDirectFinal ? (
                    <>
                      <Button
                        size="xs"
                        color="teal"
                        onClick={() => {
                          setSelectedApp(app);
                          setActionType("APPROVE");
                          setDecisionModalOpen(true);
                        }}
                      >
                        Approve (Final)
                      </Button>
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        onClick={() => {
                          setSelectedApp(app);
                          setActionType("REJECT");
                          setDecisionModalOpen(true);
                        }}
                      >
                        Reject
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        size="xs"
                        color="blue"
                        leftSection={<FaThumbsUp size={10} />}
                        onClick={() => {
                          setSelectedApp(app);
                          setActionType("RECOMMEND");
                          setDecisionModalOpen(true);
                        }}
                      >
                        Recommend
                      </Button>
                      <Button
                        size="xs"
                        color="orange"
                        variant="light"
                        leftSection={<FaThumbsDown size={10} />}
                        onClick={() => {
                          setSelectedApp(app);
                          setActionType("NOT_RECOMMEND");
                          setDecisionModalOpen(true);
                        }}
                      >
                        Not Recommend
                      </Button>
                    </>
                  )}
                </Group>
              );
            })}
          </Tabs.Panel>

          <Tabs.Panel value="higher_sanction" pt="md">
            <Alert color="violet" mb="md">
              Higher Sanction Authority queue for SCL, EL, COL, and VL requests recommended by Unit Heads (BR-EL-018).
            </Alert>
            {renderTable(applications, loading, (app) => (
              <Group gap="xs">
                <Button
                  size="xs"
                  color="teal"
                  onClick={() => {
                    setSelectedApp(app);
                    setActionType("APPROVE");
                    setDecisionModalOpen(true);
                  }}
                >
                  Sanction & Approve
                </Button>
                <Button
                  size="xs"
                  color="red"
                  variant="light"
                  onClick={() => {
                    setSelectedApp(app);
                    setActionType("REJECT");
                    setDecisionModalOpen(true);
                  }}
                >
                  Reject
                </Button>
              </Group>
            ))}
          </Tabs.Panel>
        </Tabs>
      </Card>

      {/* Decision Modal */}
      <Modal
        opened={decisionModalOpen}
        onClose={() => setDecisionModalOpen(false)}
        title={`Execute Action: ${actionType} (App #${selectedApp?.id})`}
      >
        <Stack gap="md">
          <Text size="sm">
            Applicant: <b>{selectedApp?.applicant_username}</b> | Category: <b>{selectedApp?.leave_type_code}</b> ({selectedApp?.days_count} days)
          </Text>
          <Textarea
            label="Decision Remarks / Endorsement"
            placeholder="Official remarks..."
            value={remarks}
            onChange={(e) => setRemarks(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDecisionModalOpen(false)}>
              Cancel
            </Button>
            <Button color="blue" onClick={submitDecision}>
              Confirm {actionType}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}

function renderTable(
  items: AppRecord[],
  loading: boolean,
  actionRenderer: (app: AppRecord) => React.ReactNode
) {
  if (loading) {
    return (
      <Center py="xl">
        <Loader size="lg" />
      </Center>
    );
  }

  if (items.length === 0) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        No pending items in this queue.
      </Text>
    );
  }

  return (
    <Table striped highlightOnHover withTableBorder>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>ID</Table.Th>
          <Table.Th>Applicant</Table.Th>
          <Table.Th>Category</Table.Th>
          <Table.Th>Dates</Table.Th>
          <Table.Th>Days</Table.Th>
          <Table.Th>Reason</Table.Th>
          <Table.Th>Status / Rec.</Table.Th>
          <Table.Th>Actions</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {items.map((app) => (
          <Table.Tr key={app.id}>
            <Table.Td>#{app.id}</Table.Td>
            <Table.Td fw={600}>{app.applicant_username}</Table.Td>
            <Table.Td>
              <Badge variant="outline">{app.leave_type_code}</Badge>
            </Table.Td>
            <Table.Td>
              {app.start_date} to {app.end_date}
            </Table.Td>
            <Table.Td>{app.days_count}</Table.Td>
            <Table.Td>{app.reason}</Table.Td>
            <Table.Td>
              <Badge color="blue">{app.status}</Badge>
              {app.unit_head_recommendation !== "NONE" && (
                <Text size="xs" c="dimmed">
                  Rec: {app.unit_head_recommendation}
                </Text>
              )}
            </Table.Td>
            <Table.Td>{actionRenderer(app)}</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}