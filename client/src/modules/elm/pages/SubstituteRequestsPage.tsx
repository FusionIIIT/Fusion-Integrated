import { useState } from "react";
import { Badge, Button, Group, Modal, Stack, Text, TextInput } from "@mantine/core";
import { FaCheck, FaTimes } from "react-icons/fa";
import { Column, DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useSubstituteRespondMutation, useSubstituteTasks } from "../api/hooks";
import type { LeaveApplication } from "../api/types";

export default function SubstituteRequestsPage() {
  const { data: tasks = [], isLoading, refetch } = useSubstituteTasks();
  const respondMutation = useSubstituteRespondMutation();

  const [declineModalApp, setDeclineModalApp] = useState<LeaveApplication | null>(null);
  const [declinedReason, setDeclinedReason] = useState("");

  const handleAccept = async (appId: number) => {
    await respondMutation.mutateAsync({
      applicationId: appId,
      accept: true,
    });
    refetch();
  };

  const handleDeclineSubmit = async () => {
    if (!declineModalApp) return;
    await respondMutation.mutateAsync({
      applicationId: declineModalApp.id,
      accept: false,
      declined_reason: declinedReason,
    });
    setDeclineModalApp(null);
    setDeclinedReason("");
    refetch();
  };

  const columns: Column<LeaveApplication>[] = [
    {
      key: "id",
      header: "Application",
      render: (r) => <Text fw={500}>#{r.id}</Text>,
    },
    {
      key: "applicant",
      header: "Applicant Employee",
      render: (r) => <Text size="sm">Employee #{r.employee_id}</Text>,
    },
    {
      key: "category",
      header: "Category",
      render: (r) => (
        <Group gap="xs">
          <Badge variant="outline">{r.leave_type_code}</Badge>
          <Text size="sm">{r.leave_type_name}</Text>
        </Group>
      ),
    },
    {
      key: "dates",
      header: "Period",
      render: (r) => (
        <Text size="sm">
          {r.start_date} to {r.end_date} ({r.days}d)
        </Text>
      ),
    },
    {
      key: "reason",
      header: "Reason",
      render: (r) => <Text size="sm" lineClamp={1}>{r.reason}</Text>,
    },
    {
      key: "actions",
      header: "Respond",
      align: "right",
      render: (r) => (
        <Group gap="xs" justify="flex-end">
          <Button
            size="xs"
            color="green"
            leftSection={<FaCheck size={12} />}
            loading={respondMutation.isPending}
            onClick={() => handleAccept(r.id)}
          >
            Accept
          </Button>
          <Button
            size="xs"
            color="red"
            variant="light"
            leftSection={<FaTimes size={12} />}
            onClick={() => setDeclineModalApp(r)}
          >
            Decline
          </Button>
        </Group>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Substitute Responsibility Requests"
        subtitle="Colleagues who have nominated you as their substitute during their leave absence"
      />

      <DataTable
        rows={tasks}
        columns={columns}
        loading={isLoading}
        rowKey={(r) => r.id}
        empty={{
          title: "No pending substitute requests",
          description: "You have no active substitute requests awaiting your consent.",
        }}
      />

      <Modal
        opened={Boolean(declineModalApp)}
        onClose={() => setDeclineModalApp(null)}
        title="Decline Substitute Responsibility"
      >
        <Stack gap="md">
          <Text size="sm">
            Per BR-EL-015, declining leaves the consent gate closed and notifies the applicant so they can nominate another colleague or withdraw.
          </Text>
          <TextInput
            label="Reason for Declining (Optional)"
            placeholder="Why are you unable to cover this period?"
            value={declinedReason}
            onChange={(e) => setDeclinedReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setDeclineModalApp(null)}>
              Cancel
            </Button>
            <Button color="red" onClick={handleDeclineSubmit} loading={respondMutation.isPending}>
              Confirm Decline
            </Button>
          </Group>
        </Stack>
      </Modal>
    </div>
  );
}
