import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Text,
  TextInput,
  Textarea,
  Badge,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCalendarCheck, FaTimes, FaInbox } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { usePendingSeminars, useScheduleSeminar, useRejectSeminar } from "../api/hooks";
import type { SeminarRequest } from "../api/types";

export default function PendingSchedulingPage() {
  const { data, isPending, error } = usePendingSeminars();
  const scheduleMutation = useScheduleSeminar();
  const rejectMutation = useRejectSeminar();

  const [activeRequest, setActiveRequest] = useState<SeminarRequest | null>(null);
  const [rejectingRequest, setRejectingRequest] = useState<SeminarRequest | null>(null);

  // Form states for scheduling
  const [date, setDate] = useState("");
  const [startTime, setStartTime] = useState("15:00");
  const [endTime, setEndTime] = useState("16:30");
  const [venue, setVenue] = useState("");
  const [sessionChair, setSessionChair] = useState("");
  const [remarks, setRemarks] = useState("");

  // Reject state
  const [rejectReason, setRejectReason] = useState("");

  if (error) return <Container size="xl"><ErrorState error={error} /></Container>;

  const pending = data ?? [];

  function openScheduleModal(r: SeminarRequest) {
    setActiveRequest(r);
    setDate(r.preferred_date || "");
    setVenue("Seminar Hall 1");
    setSessionChair(r.faculty_advisor_name || "");
    setRemarks("");
  }

  function handleSchedule() {
    if (!activeRequest) return;
    if (!date || !startTime || !endTime || !venue.trim()) {
      notifications.show({ color: "red", message: "Date, times, and venue are required." });
      return;
    }

    scheduleMutation.mutate(
      {
        id: activeRequest.id,
        data: {
          scheduled_date: date,
          start_time: startTime + ":00",
          end_time: endTime + ":00",
          venue: venue.trim(),
          session_chair: sessionChair.trim(),
          remarks: remarks.trim(),
        },
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Seminar Scheduled",
            message: `Seminar for '${activeRequest.topic}' scheduled successfully (OA-UC-53).`,
          });
          setActiveRequest(null);
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Scheduling Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  function handleReject() {
    if (!rejectingRequest) return;
    if (!rejectReason.trim()) {
      notifications.show({ color: "red", message: "Please provide a rejection reason." });
      return;
    }

    rejectMutation.mutate(
      { id: rejectingRequest.id, reason: rejectReason.trim() },
      {
        onSuccess: () => {
          notifications.show({
            color: "gray",
            title: "Request Rejected",
            message: `Seminar request #${rejectingRequest.id} has been rejected.`,
          });
          setRejectingRequest(null);
          setRejectReason("");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Action Failed",
            message: errorMessage(err),
          });
        },
      }
    );
  }

  const columns = [
    {
      key: "id",
      header: "ID",
      render: (r: SeminarRequest) => <Text fw={600} size="sm">#{r.id}</Text>,
    },
    {
      key: "speaker",
      header: "Candidate / Speaker",
      render: (r: SeminarRequest) => (
        <div>
          <Text fw={600} size="sm">{r.student_name}</Text>
          <Text size="xs" c="dimmed">ID: {r.student_id} ({r.programme})</Text>
        </div>
      ),
    },
    {
      key: "topic",
      header: "Topic & Abstract",
      render: (r: SeminarRequest) => (
        <div style={{ maxWidth: 360 }}>
          <Text fw={600} size="sm" lineClamp={1}>{r.topic}</Text>
          <Text size="xs" c="dimmed" lineClamp={2}>{r.abstract}</Text>
        </div>
      ),
    },
    {
      key: "preferred_date",
      header: "Preferred Date",
      render: (r: SeminarRequest) => (
        <Badge variant="outline" size="sm">
          {r.preferred_date || "Any time"}
        </Badge>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (r: SeminarRequest) => <StatusBadge status={r.status.toLowerCase()} />,
    },
    {
      key: "actions",
      header: "Actions",
      align: "right" as const,
      render: (r: SeminarRequest) => (
        <Group gap="xs" justify="flex-end">
          <Button
            size="xs"
            leftSection={<FaCalendarCheck />}
            onClick={() => openScheduleModal(r)}
          >
            Schedule
          </Button>
          <Button
            size="xs"
            color="red"
            variant="light"
            leftSection={<FaTimes />}
            onClick={() => setRejectingRequest(r)}
          >
            Reject
          </Button>
        </Group>
      ),
    },
  ];

  return (
    <Container size="xl">
      <PageHeader
        title="Pending Seminar Scheduling"
        subtitle="Department Administrator review and schedule queue (OA-UC-53, OA-BR-62)"
      />

      <Card padding="lg" withBorder>
        <DataTable<SeminarRequest>
          rows={pending}
          columns={columns}
          loading={isPending}
          rowKey={(r) => r.id}
          empty={{
            icon: FaInbox,
            title: "Queue Empty",
            description: "There are no seminar requests waiting to be scheduled.",
          }}
        />
      </Card>

      {/* Schedule Modal */}
      <Modal
        opened={!!activeRequest}
        onClose={() => setActiveRequest(null)}
        title={<Text fw={700}>Schedule Graduate Seminar (OA-UC-53)</Text>}
        size="lg"
      >
        {activeRequest && (
          <Stack gap="md">
            <div>
              <Text size="xs" c="dimmed">Candidate:</Text>
              <Text fw={600}>{activeRequest.student_name} ({activeRequest.programme})</Text>
              <Text size="sm" mt="xs"><b>Topic:</b> {activeRequest.topic}</Text>
            </div>

            <TextInput
              label="Seminar Date"
              type="date"
              required
              value={date}
              onChange={(e) => setDate(e.currentTarget.value)}
            />

            <Group grow>
              <TextInput
                label="Start Time"
                type="time"
                required
                value={startTime}
                onChange={(e) => setStartTime(e.currentTarget.value)}
              />
              <TextInput
                label="End Time"
                type="time"
                required
                value={endTime}
                onChange={(e) => setEndTime(e.currentTarget.value)}
              />
            </Group>

            <TextInput
              label="Venue / Hall"
              placeholder="e.g. Auditorium Hall 1 / Online Zoom"
              required
              value={venue}
              onChange={(e) => setVenue(e.currentTarget.value)}
            />

            <TextInput
              label="Session Chair / Committee Head"
              placeholder="e.g. Prof. R. K. Sen"
              value={sessionChair}
              onChange={(e) => setSessionChair(e.currentTarget.value)}
            />

            <Textarea
              label="Administrative Remarks"
              placeholder="Special instructions or scheduling notes..."
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setActiveRequest(null)}>
                Cancel
              </Button>
              <Button
                color="blue"
                leftSection={<FaCalendarCheck />}
                onClick={handleSchedule}
                loading={scheduleMutation.isPending}
              >
                Confirm & Log Schedule
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {/* Reject Modal */}
      <Modal
        opened={!!rejectingRequest}
        onClose={() => setRejectingRequest(null)}
        title={<Text fw={700} c="red">Reject Seminar Request</Text>}
      >
        <Stack gap="md">
          <Text size="sm">
            Please provide a justification for declining this seminar request:
          </Text>
          <Textarea
            placeholder="e.g. Inadequate progress report or committee unavailable."
            required
            value={rejectReason}
            onChange={(e) => setRejectReason(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setRejectingRequest(null)}>
              Cancel
            </Button>
            <Button
              color="red"
              onClick={handleReject}
              loading={rejectMutation.isPending}
            >
              Confirm Rejection
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
