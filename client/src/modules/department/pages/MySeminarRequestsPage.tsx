import { Button, Card, Container, Text, Badge } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaGraduationCap, FaPlus, FaTimes } from "react-icons/fa";
import { Link } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useSeminarRequests, useCancelSeminar } from "../api/hooks";
import type { SeminarRequest } from "../api/types";

export default function MySeminarRequestsPage() {
  const { data, isPending, error } = useSeminarRequests();
  const cancelMutation = useCancelSeminar();

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const requests = data ?? [];

  function handleCancel(id: number) {
    if (!window.confirm("Are you sure you want to cancel this pending seminar request?")) return;
    cancelMutation.mutate(id, {
      onSuccess: () => {
        notifications.show({
          color: "gray",
          title: "Request Cancelled",
          message: `Seminar request #${id} has been cancelled.`,
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Could not cancel",
          message: errorMessage(err),
        });
      },
    });
  }

  const columns = [
    {
      key: "id",
      header: "ID",
      render: (r: SeminarRequest) => <Text fw={600} size="sm">#{r.id}</Text>,
    },
    {
      key: "topic",
      header: "Topic / Title",
      render: (r: SeminarRequest) => (
        <div>
          <Text fw={600} size="sm">{r.topic}</Text>
          <Text size="xs" c="dimmed">{r.programme} - {r.department || "Department"}</Text>
        </div>
      ),
    },
    {
      key: "advisor",
      header: "Advisor",
      render: (r: SeminarRequest) => (
        <Text size="sm">{r.faculty_advisor_name || "—"}</Text>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r: SeminarRequest) => <StatusBadge status={r.status.toLowerCase()} />,
    },
    {
      key: "schedule_details",
      header: "Schedule Details",
      render: (r: SeminarRequest) => {
        if (r.seminar) {
          return (
            <div>
              <Badge color="green" variant="light" size="sm">
                {r.seminar.scheduled_date} ({r.seminar.start_time} - {r.seminar.end_time})
              </Badge>
              <Text size="xs" c="dimmed">Venue: {r.seminar.venue}</Text>
            </div>
          );
        }
        if (r.status === "AWAITING_SCHEDULING") {
          return <Text size="xs" c="blue">Pending Admin Scheduling</Text>;
        }
        if (r.status === "REJECTED" && r.rejection_reason) {
          return <Text size="xs" c="red">{r.rejection_reason}</Text>;
        }
        return <Text size="xs" c="dimmed">—</Text>;
      },
    },
    {
      key: "actions",
      header: "Actions",
      align: "right" as const,
      render: (r: SeminarRequest) => {
        if (r.status === "AWAITING_SCHEDULING") {
          return (
            <Button
              color="red"
              variant="subtle"
              size="xs"
              leftSection={<FaTimes />}
              onClick={() => handleCancel(r.id)}
              loading={cancelMutation.isPending}
            >
              Cancel
            </Button>
          );
        }
        return null;
      },
    },
  ];

  return (
    <Container size="xl">
      <PageHeader
        title="My Seminar Requests"
        subtitle="Track your graduate seminar scheduling requests and scheduled dates (BW-OAP-09)"
        action={
          <Button
            component={Link}
            to="/department/seminar-request"
            leftSection={<FaPlus />}
          >
            New Request
          </Button>
        }
      />
      <Card padding="lg" withBorder>
        <DataTable<SeminarRequest>
          rows={requests}
          columns={columns}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{
            icon: FaGraduationCap,
            title: "No Seminar Requests",
            description: "You have not submitted any graduate seminar requests yet.",
          }}
        />
      </Card>
    </Container>
  );
}
