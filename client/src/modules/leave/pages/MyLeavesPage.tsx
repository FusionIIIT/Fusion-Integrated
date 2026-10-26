import { useState } from "react";
import { Link } from "react-router-dom";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Menu,
  Select,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";
import {
  FaCalendarAlt,
  FaCalendarPlus,
  FaCheckCircle,
  FaEllipsisV,
  FaEye,
  FaRedo,
  FaTimes,
  FaUndo,
} from "react-icons/fa";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveBalances, useLeaveRequests } from "../api/hooks";
import type { LeaveRequest } from "../api/types";
import {
  CancelLeaveModal,
  ExtendLeaveModal,
  LeaveDetailModal,
  ResumeLeaveModal,
  WithdrawModal,
} from "../components/LeaveActionModals";
import { LeaveStatusBadge } from "../components/LeaveStatusBadge";

const PENDING_WITHDRAW_STATUSES = new Set([
  "draft",
  "awaiting_substitute",
  "awaiting_unit_head",
  "awaiting_establishment",
  "awaiting_sanction",
  "awaiting_director",
  "applicant_action_required",
]);

export default function MyLeavesPage() {
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [detailRequest, setDetailRequest] = useState<LeaveRequest | null>(null);
  const [withdrawRequest, setWithdrawRequest] = useState<LeaveRequest | null>(null);
  const [cancelRequest, setCancelRequest] = useState<LeaveRequest | null>(null);
  const [extendRequest, setExtendRequest] = useState<LeaveRequest | null>(null);
  const [resumeRequest, setResumeRequest] = useState<LeaveRequest | null>(null);

  const {
    data: balances,
    isPending: balancesLoading,
    error: balancesError,
  } = useLeaveBalances();

  const {
    data: requests,
    isPending: requestsLoading,
    error: requestsError,
  } = useLeaveRequests(statusFilter ? { status: statusFilter } : undefined);

  if (balancesError) {
    return (
      <Container size="xl">
        <ErrorState error={balancesError} />
      </Container>
    );
  }

  const todayStr = new Date().toISOString().split("T")[0] || "";

  return (
    <Container size="xl">
      <PageHeader
        title="My Leaves"
        subtitle="Manage your leave entitlements, check balances, and track applications."
        action={
          <Button
            component={Link}
            to="/leave/apply"
            leftSection={<FaCalendarPlus />}
            variant="filled"
          >
            Apply for Leave
          </Button>
        }
      />

      {/* Leave Balances Section */}
      <Stack gap="xs" mb="lg">
        <Text fw={700} size="md">
          Current Year Balances ({new Date().getFullYear()})
        </Text>
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3, lg: 4 }} spacing="md">
          {balancesLoading && (
            <Card withBorder padding="md">
              <Text size="sm" c="dimmed">
                Loading leave balances...
              </Text>
            </Card>
          )}

          {!balancesLoading && (!balances || balances.length === 0) && (
            <Card withBorder padding="md">
              <Text size="sm" c="dimmed">
                No leave balance records found for the current calendar year.
              </Text>
            </Card>
          )}

          {balances?.map((b) => (
            <Card key={b.id} withBorder padding="md" radius="md">
              <Group justify="space-between" mb="xs">
                <Text fw={700} size="sm">
                  {b.leave_type?.name}
                </Text>
                <Badge variant="filled" color="blue" size="sm">
                  {b.leave_type?.code}
                </Badge>
              </Group>
              <Group align="flex-end" justify="space-between">
                <div>
                  <Text size="xs" c="dimmed">
                    Available
                  </Text>
                  <Text size="xl" fw={800} c="blue">
                    {b.available_days}
                  </Text>
                </div>
                <div style={{ textAlign: "right" }}>
                  <Text size="xs" c="dimmed">
                    Used: {b.used_days}
                  </Text>
                  <Text size="xs" c="dimmed">
                    Credited: {b.credited_days}
                  </Text>
                </div>
              </Group>
            </Card>
          ))}
        </SimpleGrid>
      </Stack>

      {/* Requests History Section */}
      <Card withBorder padding="lg" radius="md">
        <Group justify="space-between" mb="md" wrap="wrap">
          <Text fw={700} size="md">
            Leave Applications & History
          </Text>
          <Select
            size="xs"
            placeholder="Filter by status"
            clearable
            value={statusFilter}
            onChange={setStatusFilter}
            data={[
              { value: "awaiting_substitute", label: "Awaiting Substitute" },
              { value: "awaiting_unit_head", label: "Awaiting Unit Head" },
              { value: "awaiting_sanction", label: "Awaiting Sanction" },
              { value: "approved", label: "Approved" },
              { value: "rejected", label: "Rejected" },
              { value: "withdrawn", label: "Withdrawn" },
              { value: "cancelled", label: "Cancelled" },
              { value: "extended", label: "Extended" },
              { value: "resumption_review_pending", label: "Resumption Pending" },
            ]}
          />
        </Group>

        {requestsError && <ErrorState error={requestsError} />}

        <DataTable<LeaveRequest>
          rows={(requests ?? []) as LeaveRequest[]}
          loading={requestsLoading}
          rowKey={(r) => r.id}
          minWidth={850}
          columns={[
            {
              key: "application_number",
              header: "Application #",
              render: (r) => (
                <Stack gap={0}>
                  <Text fw={600} size="sm">
                    {r.application_number}
                  </Text>
                  <Text size="xs" c="dimmed">
                    {r.leave_type?.name} ({r.leave_type?.code})
                  </Text>
                </Stack>
              ),
            },
            {
              key: "dates",
              header: "Dates",
              render: (r) => (
                <Stack gap={0}>
                  <Text size="sm">
                    {r.start_date} → {r.end_date}
                  </Text>
                  <Group gap={4}>
                    <Text size="xs" c="dimmed">
                      {r.requested_days} days
                    </Text>
                    {r.is_half_day && (
                      <Badge size="xs" color="blue" variant="outline">
                        Half Day
                      </Badge>
                    )}
                    {r.is_station_leave && (
                      <Badge size="xs" color="gray" variant="outline">
                        Station Leave
                      </Badge>
                    )}
                  </Group>
                </Stack>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <LeaveStatusBadge status={r.status} />,
            },
            {
              key: "stage",
              header: "Handler / Stage",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {r.current_handler_role || "Finished"}
                </Text>
              ),
            },
            {
              key: "actions",
              header: "Actions",
              align: "right",
              render: (r) => {
                const canWithdraw = PENDING_WITHDRAW_STATUSES.has(r.status);
                const canCancel =
                  r.status === "approved" && r.start_date >= todayStr;
                const canExtend =
                  (r.status === "approved" || r.status === "extended") &&
                  r.leave_type?.allows_extension;
                const canResume =
                  (r.status === "approved" || r.status === "extended") &&
                  ["EL", "COL", "VL"].includes(r.leave_type?.code);

                return (
                  <Group justify="flex-end" gap="xs">
                    <Button
                      size="xs"
                      variant="subtle"
                      leftSection={<FaEye size={12} />}
                      onClick={() => setDetailRequest(r)}
                    >
                      Details
                    </Button>

                    {(canWithdraw || canCancel || canExtend || canResume) && (
                      <Menu position="bottom-end" shadow="md">
                        <Menu.Target>
                          <ActionIcon variant="subtle" color="gray" size="sm">
                            <FaEllipsisV size={12} />
                          </ActionIcon>
                        </Menu.Target>
                        <Menu.Dropdown>
                          {canWithdraw && (
                            <Menu.Item
                              color="red"
                              leftSection={<FaUndo size={12} />}
                              onClick={() => setWithdrawRequest(r)}
                            >
                              Withdraw Application
                            </Menu.Item>
                          )}
                          {canCancel && (
                            <Menu.Item
                              color="yellow"
                              leftSection={<FaTimes size={12} />}
                              onClick={() => setCancelRequest(r)}
                            >
                              Request Cancellation
                            </Menu.Item>
                          )}
                          {canExtend && (
                            <Menu.Item
                              color="teal"
                              leftSection={<FaRedo size={12} />}
                              onClick={() => setExtendRequest(r)}
                            >
                              Request Extension
                            </Menu.Item>
                          )}
                          {canResume && (
                            <Menu.Item
                              color="blue"
                              leftSection={<FaCheckCircle size={12} />}
                              onClick={() => setResumeRequest(r)}
                            >
                              Submit Duty Resumption
                            </Menu.Item>
                          )}
                        </Menu.Dropdown>
                      </Menu>
                    )}
                  </Group>
                );
              },
            },
          ]}
          empty={{
            icon: FaCalendarAlt,
            title: "No leave applications yet",
            description: "When you apply for leaves, your applications will appear here.",
          }}
        />
      </Card>

      {/* Action Modals */}
      <LeaveDetailModal
        request={detailRequest}
        opened={detailRequest !== null}
        onClose={() => setDetailRequest(null)}
      />

      <WithdrawModal
        request={withdrawRequest}
        opened={withdrawRequest !== null}
        onClose={() => setWithdrawRequest(null)}
      />

      <CancelLeaveModal
        request={cancelRequest}
        opened={cancelRequest !== null}
        onClose={() => setCancelRequest(null)}
      />

      <ExtendLeaveModal
        request={extendRequest}
        opened={extendRequest !== null}
        onClose={() => setExtendRequest(null)}
      />

      <ResumeLeaveModal
        request={resumeRequest}
        opened={resumeRequest !== null}
        onClose={() => setResumeRequest(null)}
      />
    </Container>
  );
}
