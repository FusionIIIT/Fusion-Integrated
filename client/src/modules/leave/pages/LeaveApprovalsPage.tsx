import React, { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTasks, FaTimes } from "react-icons/fa";

import { http } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

interface LeaveRequest {
  id: number;
  user_id: number;
  category: string;
  start_date: string;
  end_date: string;
  requested_days: string;
  purpose: string;
  status: string;
  substitute_user_id: number | null;
  station_leave: boolean;
}

export default function LeaveApprovalsPage() {
  const [substituteRequests, setSubstituteRequests] = useState<LeaveRequest[]>([]);
  const [approvalRequests, setApprovalRequests] = useState<LeaveRequest[]>([]);
  const [remarks, setRemarks] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [subRes, appRes] = await Promise.all([
        http.get<LeaveRequest[]>("/api/v1/leave/substitute-queue/"),
        http.get<LeaveRequest[]>("/api/v1/leave/approvals-queue/"),
      ]);
      setSubstituteRequests(subRes.data);
      setApprovalRequests(appRes.data);
    } catch {
      notifications.show({
        color: "red",
        title: "Error",
        message: "Failed to load approval queues",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubstituteResponse = async (id: number, accept: boolean) => {
    try {
      await http.post(`/api/v1/leave/substitute-queue/${id}/respond/`, {
        accept,
        remarks: remarks[id] || "",
      });
      notifications.show({
        color: "green",
        title: "Success",
        message: accept ? "Substitute responsibility accepted" : "Substitute request declined",
      });
      loadData();
    } catch {
      notifications.show({ color: "red", title: "Error", message: "Failed to submit response" });
    }
  };

  const handleDecision = async (id: number, decision: string) => {
    try {
      await http.post(`/api/v1/leave/approvals-queue/${id}/decide/`, {
        decision,
        remarks: remarks[id] || "",
      });
      notifications.show({
        color: "green",
        title: "Success",
        message: `Leave request ${decision}`,
      });
      loadData();
    } catch {
      notifications.show({ color: "red", title: "Error", message: "Failed to submit decision" });
    }
  };

  return (
    <Container size="xl" py="lg">
      <Stack gap="lg">
        <PageHeader
          title="Leave Approvals & Tasks"
          description="Review actionable substitute requests and leave applications awaiting review or sanction"
          icon={<FaTasks size={22} />}
        />

        <Tabs defaultValue="approvals">
          <Tabs.List>
            <Tabs.Tab value="approvals">
              Review & Sanction Queue ({approvalRequests.length})
            </Tabs.Tab>
            <Tabs.Tab value="substitute">
              Substitute Requests ({substituteRequests.length})
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="approvals" pt="md">
            <Card shadow="xs" padding="md" radius="md" withBorder>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Applicant</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Dates</Table.Th>
                    <Table.Th>Days</Table.Th>
                    <Table.Th>Purpose</Table.Th>
                    <Table.Th>Status</Table.Th>
                    <Table.Th>Remarks & Decision</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {approvalRequests.length === 0 ? (
                    <Table.Tr>
                      <Table.Td colSpan={7} style={{ textAlign: "center" }}>
                        {loading ? "Loading..." : "No requests pending approval."}
                      </Table.Td>
                    </Table.Tr>
                  ) : (
                    approvalRequests.map((r) => (
                      <Table.Tr key={r.id}>
                        <Table.Td>User #{r.user_id}</Table.Td>
                        <Table.Td>
                          <Badge variant="outline">{r.category}</Badge>
                        </Table.Td>
                        <Table.Td>
                          {r.start_date} to {r.end_date}
                        </Table.Td>
                        <Table.Td>{r.requested_days}</Table.Td>
                        <Table.Td>{r.purpose}</Table.Td>
                        <Table.Td>
                          <Badge color="blue">{r.status.replace(/_/g, " ")}</Badge>
                        </Table.Td>
                        <Table.Td>
                          <Stack gap="xs">
                            <Textarea
                              size="xs"
                              placeholder="Reviewer remarks"
                              value={remarks[r.id] || ""}
                              onChange={(e) =>
                                setRemarks({ ...remarks, [r.id]: e.target.value })
                              }
                            />
                            <Group gap="xs">
                              {r.category === "CL" || r.category === "RH" ? (
                                <>
                                  <Button
                                    size="xs"
                                    color="green"
                                    leftSection={<FaCheck size={12} />}
                                    onClick={() => handleDecision(r.id, "approved")}
                                  >
                                    Approve
                                  </Button>
                                  <Button
                                    size="xs"
                                    color="red"
                                    leftSection={<FaTimes size={12} />}
                                    onClick={() => handleDecision(r.id, "rejected")}
                                  >
                                    Reject
                                  </Button>
                                </>
                              ) : (
                                <>
                                  <Button
                                    size="xs"
                                    color="teal"
                                    onClick={() => handleDecision(r.id, "recommended")}
                                  >
                                    Recommend
                                  </Button>
                                  <Button
                                    size="xs"
                                    color="orange"
                                    onClick={() => handleDecision(r.id, "not_recommended")}
                                  >
                                    Not Recommend
                                  </Button>
                                  <Button
                                    size="xs"
                                    color="green"
                                    onClick={() => handleDecision(r.id, "approved")}
                                  >
                                    Sanction
                                  </Button>
                                </>
                              )}
                            </Group>
                          </Stack>
                        </Table.Td>
                      </Table.Tr>
                    ))
                  )}
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>

          <Tabs.Panel value="substitute" pt="md">
            <Card shadow="xs" padding="md" radius="md" withBorder>
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Applicant</Table.Th>
                    <Table.Th>Category</Table.Th>
                    <Table.Th>Dates</Table.Th>
                    <Table.Th>Days</Table.Th>
                    <Table.Th>Purpose</Table.Th>
                    <Table.Th>Actions</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {substituteRequests.length === 0 ? (
                    <Table.Tr>
                      <Table.Td colSpan={6} style={{ textAlign: "center" }}>
                        {loading ? "Loading..." : "No substitute requests pending."}
                      </Table.Td>
                    </Table.Tr>
                  ) : (
                    substituteRequests.map((r) => (
                      <Table.Tr key={r.id}>
                        <Table.Td>User #{r.user_id}</Table.Td>
                        <Table.Td>
                          <Badge variant="outline">{r.category}</Badge>
                        </Table.Td>
                        <Table.Td>
                          {r.start_date} to {r.end_date}
                        </Table.Td>
                        <Table.Td>{r.requested_days}</Table.Td>
                        <Table.Td>{r.purpose}</Table.Td>
                        <Table.Td>
                          <Group gap="xs">
                            <Button
                              size="xs"
                              color="green"
                              onClick={() => handleSubstituteResponse(r.id, true)}
                            >
                              Accept
                            </Button>
                            <Button
                              size="xs"
                              color="red"
                              onClick={() => handleSubstituteResponse(r.id, false)}
                            >
                              Decline
                            </Button>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))
                  )}
                </Table.Tbody>
              </Table>
            </Card>
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Container>
  );
}
