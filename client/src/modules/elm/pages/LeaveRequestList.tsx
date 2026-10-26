import { useState } from "react";
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
} from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveRequests, usePendingApprovals } from "../api";
import { LeaveBalancesCard } from "./LeaveBalancesCard";
import { LeaveRequestDetailModal } from "./LeaveRequestDetailModal";
import type { LeaveRequest, LeaveStatus } from "../types";

const STATUS_COLORS: Record<LeaveStatus, string> = {
  draft: "gray",
  submitted: "blue",
  pending_substitute: "yellow",
  substitute_declined: "red",
  pending_unit_head: "blue",
  pending_sanction: "indigo",
  awaiting_director_self_sanction: "violet",
  approved: "teal",
  rejected: "red",
  withdrawn: "gray",
  cancellation_pending_unit_head: "orange",
  cancellation_pending_sanction: "orange",
  cancelled: "dark",
};

export default function LeaveRequestList() {
  const [selectedRequest, setSelectedRequest] = useState<LeaveRequest | null>(null);
  const [modalOpened, setModalOpened] = useState(false);

  const { data: myRequests, isLoading: myLoading } = useLeaveRequests();
  const { data: inboxItems, isLoading: inboxLoading } = usePendingApprovals();

  const handleOpenDetail = (req: LeaveRequest) => {
    setSelectedRequest(req);
    setModalOpened(true);
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Employee Leave Management"
        subtitle="Manage leave balances, applications, substitute responses, and approvals"
        action={
          <Button component={Link} to="/elm/leave-requests/create">
            Apply for Leave
          </Button>
        }
      />

      <Stack gap="lg" mt="md">
        {/* Entitlements & Balance Ledger (EL-UC-012) */}
        <div>
          <Text fw={600} size="md" mb="xs">
            Annual Leave Entitlements & Balances
          </Text>
          <LeaveBalancesCard />
        </div>

        {/* Requests and Approvals Tabs */}
        <Card padding="md" withBorder radius="md">
          <Tabs defaultValue="my-requests">
            <Tabs.List mb="md">
              <Tabs.Tab value="my-requests">
                My Leave Requests {myRequests && `(${myRequests.length})`}
              </Tabs.Tab>
              <Tabs.Tab value="inbox">
                Pending Approvals & Inbox {inboxItems && inboxItems.length > 0 && (
                  <Badge size="xs" color="red" ml={4}>
                    {inboxItems.length}
                  </Badge>
                )}
              </Tabs.Tab>
            </Tabs.List>

            {/* Tab: My Requests */}
            <Tabs.Panel value="my-requests">
              {myLoading ? (
                <Text c="dimmed">Loading leave requests...</Text>
              ) : !myRequests || myRequests.length === 0 ? (
                <Text c="dimmed">No leave requests found.</Text>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Leave Period</Table.Th>
                      <Table.Th>Days</Table.Th>
                      <Table.Th>Substitute</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {myRequests.map((req) => (
                      <Table.Tr key={req.id}>
                        <Table.Td>#{req.id}</Table.Td>
                        <Table.Td>
                          <Badge variant="outline" size="sm">
                            {req.category.toUpperCase()}
                          </Badge>
                          {req.half_day && (
                            <Badge color="cyan" size="xs" ml={4}>
                              0.5d
                            </Badge>
                          )}
                        </Table.Td>
                        <Table.Td>
                          {req.start_date} to {req.end_date}
                        </Table.Td>
                        <Table.Td>{req.leave_days || `${req.estimated_calendar_interval} (est.)`}</Table.Td>
                        <Table.Td>
                          {req.substitute_id ? (
                            <Text size="xs">
                              User #{req.substitute_id} ({req.substitute_status})
                            </Text>
                          ) : (
                            <Text size="xs" c="dimmed">None</Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Badge color={STATUS_COLORS[req.status] || "gray"} size="sm">
                            {req.status.replace(/_/g, " ")}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Button size="xs" variant="light" onClick={() => handleOpenDetail(req)}>
                            View / Manage
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>

            {/* Tab: Inbox */}
            <Tabs.Panel value="inbox">
              {inboxLoading ? (
                <Text c="dimmed">Loading actionable approvals...</Text>
              ) : !inboxItems || inboxItems.length === 0 ? (
                <Text c="dimmed">No pending action items in your approval inbox.</Text>
              ) : (
                <Table striped highlightOnHover>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Applicant</Table.Th>
                      <Table.Th>Category</Table.Th>
                      <Table.Th>Period</Table.Th>
                      <Table.Th>Days</Table.Th>
                      <Table.Th>Pending State</Table.Th>
                      <Table.Th>Action Required</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {inboxItems.map((item) => (
                      <Table.Tr key={item.id}>
                        <Table.Td>#{item.id}</Table.Td>
                        <Table.Td>User #{item.user_id}</Table.Td>
                        <Table.Td>
                          <Badge variant="outline" size="sm">
                            {item.category.toUpperCase()}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          {item.start_date} to {item.end_date}
                        </Table.Td>
                        <Table.Td>{item.leave_days || `${item.estimated_calendar_interval} (est.)`}</Table.Td>
                        <Table.Td>
                          <Badge color={STATUS_COLORS[item.status] || "yellow"} size="sm">
                            {item.status.replace(/_/g, " ")}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Button size="xs" color="teal" onClick={() => handleOpenDetail(item)}>
                            Review & Act
                          </Button>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Tabs.Panel>
          </Tabs>
        </Card>
      </Stack>

      <LeaveRequestDetailModal
        opened={modalOpened}
        onClose={() => setModalOpened(false)}
        request={selectedRequest}
      />
    </Container>
  );
}
