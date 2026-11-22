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
  Text,
  TextInput,
  Textarea,
  Timeline,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarAlt, FaCheck, FaHistory, FaPlus } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useApplyLeave, useLeaves, useMyServiceRecord } from "../api/hooks";
import type { LeaveRequest } from "../api/types";

export default function LeavesPage() {
  const { data: leaves, isPending, error } = useLeaves();
  const { data: serviceRecord } = useMyServiceRecord();
  const applyMutation = useApplyLeave();
  const { can } = useAuth();

  const [modalOpen, setModalOpen] = useState(false);
  const [historyTarget, setHistoryTarget] = useState<LeaveRequest | null>(null);

  // Form states
  const [leaveType, setLeaveType] = useState<string>("casual");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [durationDays, setDurationDays] = useState<number>(1);
  const [justification, setJustification] = useState<string>("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleApply = (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate || !justification) {
      notifications.show({
        title: "Validation Error",
        message: "Please fill in all required fields.",
        color: "red",
      });
      return;
    }

    applyMutation.mutate(
      {
        leave_type: leaveType,
        start_date: startDate,
        end_date: endDate,
        duration_days: durationDays,
        justification,
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Leave Submitted",
            message: "Your leave application has been submitted to your approving authority.",
            color: "teal",
          });
          setModalOpen(false);
          setJustification("");
          setStartDate("");
          setEndDate("");
        },
        onError: (err) => {
          notifications.show({
            title: "Application Failed",
            message: errorMessage(err),
            color: "red",
          });
        },
      }
    );
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Leave Management"
        subtitle="Apply for leave, track application routing, and verify remaining quotas (BR-HR-007, BR-HR-008)"
        action={
          can("hr_eis.leave.apply") && (
            <Button
              leftSection={<FaPlus size={12} />}
              onClick={() => setModalOpen(true)}
              color="blue"
            >
              Apply for Leave
            </Button>
          )
        }
      />

      <Card padding="lg" withBorder radius="md">
        <DataTable<LeaveRequest>
          rows={leaves ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={850}
          empty={{
            icon: FaCalendarAlt,
            title: "No leave records found",
            description: "You have not submitted any leave applications yet.",
          }}
          columns={[
            {
              key: "leave_type",
              header: "Type",
              render: (r) => (
                <Text fw={600} size="sm" tt="capitalize">
                  {r.leave_type}
                </Text>
              ),
            },
            {
              key: "dates",
              header: "Duration",
              render: (r) => (
                <Text size="sm">
                  {r.start_date} to {r.end_date} ({r.duration_days} d)
                </Text>
              ),
            },
            {
              key: "justification",
              header: "Reason",
              render: (r) => (
                <Text size="sm" lineClamp={1}>
                  {r.justification}
                </Text>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "current_authority",
              header: "Current Authority",
              render: (r) => (
                <Badge variant="outline" color="gray" size="sm">
                  {r.current_authority_role?.toUpperCase()}
                </Badge>
              ),
            },
            {
              key: "applied_at",
              header: "Submitted",
              render: (r) => (
                <Text size="xs" c="dimmed">
                  {new Date(r.created_at).toLocaleDateString()}
                </Text>
              ),
            },
            {
              key: "actions",
              header: "Workflow",
              render: (r) => (
                <Button
                  size="xs"
                  variant="subtle"
                  leftSection={<FaHistory size={10} />}
                  onClick={() => setHistoryTarget(r)}
                >
                  History
                </Button>
              ),
            },
          ]}
        />
      </Card>

      {/* Apply Leave Modal */}
      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Apply for Leave"
        size="md"
      >
        <form onSubmit={handleApply}>
          <Stack gap="md">
            <Select
              label="Leave Type"
              required
              value={leaveType}
              onChange={(v) => v && setLeaveType(v)}
              data={[
                { value: "casual", label: "Casual Leave" },
                { value: "restricted", label: "Restricted Holiday" },
                { value: "medical", label: "Medical Leave" },
                { value: "earned", label: "Earned Leave" },
                { value: "vacation", label: "Vacation Leave" },
                ...(serviceRecord?.category === "faculty"
                  ? [{ value: "sabbatical", label: "Sabbatical Leave (Faculty Only)" }]
                  : []),
              ]}
            />

            <Group grow>
              <TextInput
                label="Start Date"
                type="date"
                required
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
              <TextInput
                label="End Date"
                type="date"
                required
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </Group>

            <NumberInput
              label="Duration in Days"
              required
              min={0.5}
              step={0.5}
              value={durationDays}
              onChange={(val) => setDurationDays(Number(val) || 1)}
            />

            <Textarea
              label="Reason / Justification"
              required
              placeholder="State clear purpose of leave..."
              rows={3}
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={applyMutation.isPending} color="blue">
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>

      {/* Decision History Modal */}
      <Modal
        opened={historyTarget != null}
        onClose={() => setHistoryTarget(null)}
        title="Approval Workflow History"
        size="md"
      >
        {historyTarget && (
          <Stack gap="md">
            <Text size="sm" fw={600}>
              {historyTarget.leave_type.toUpperCase()} Leave ({historyTarget.duration_days} days)
            </Text>
            {historyTarget.decision_history.length === 0 ? (
              <Text size="sm" c="dimmed">
                No decisions recorded yet. Request is currently awaiting review by {historyTarget.current_authority_role.toUpperCase()}.
              </Text>
            ) : (
              <Timeline active={historyTarget.decision_history.length - 1} bulletSize={20} lineWidth={2}>
                {historyTarget.decision_history.map((step, idx) => (
                  <Timeline.Item
                    key={idx}
                    bullet={<FaCheck size={10} />}
                    title={`${step.role.toUpperCase()} - ${step.outcome.toUpperCase()}`}
                  >
                    <Text size="xs" c="dimmed">
                      By {step.actor_username} on {new Date(step.timestamp).toLocaleString()}
                    </Text>
                    {step.remarks && (
                      <Text size="sm" mt={4}>
                        "{step.remarks}"
                      </Text>
                    )}
                  </Timeline.Item>
                ))}
              </Timeline>
            )}
          </Stack>
        )}
      </Modal>
    </Container>
  );
}
