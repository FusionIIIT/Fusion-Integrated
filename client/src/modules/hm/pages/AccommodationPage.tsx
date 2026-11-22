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
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAccommodationRequests, useSubmitAccommodationRequest } from "../api/hooks";
import type { AccommodationRequest } from "../api/types";

export default function AccommodationPage() {
  const { data, isPending, error } = useAccommodationRequests();
  const submitMutation = useSubmitAccommodationRequest();

  const [modalOpen, setModalOpen] = useState(false);
  const [preferredRoomType, setPreferredRoomType] = useState("");
  const [reason, setReason] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleSubmit() {
    submitMutation.mutate(
      { preferred_room_type: preferredRoomType, reason },
      {
        onSuccess: () => {
          notifications.show({
            title: "Success",
            message: "Accommodation request submitted",
            color: "green",
          });
          setModalOpen(false);
          setPreferredRoomType("");
          setReason("");
        },
        onError: (err: any) => {
          notifications.show({
            title: "Error",
            message: err?.message || "Failed to submit request",
            color: "red",
          });
        },
      }
    );
  }

  return (
    <Container size="xl">
      <Group justify="space-between" mb="md">
        <PageHeader
          title="Accommodation Requests"
          subtitle="Submit and monitor your hostel room accommodation requests"
        />
        <Button onClick={() => setModalOpen(true)}>New Request</Button>
      </Group>

      <Card padding="lg">
        <DataTable<AccommodationRequest>
          rows={data ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "id", header: "ID", render: (r) => `#${r.id}` },
            { key: "user_id", header: "Student ID" },
            { key: "preferred_room_type", header: "Room Type" },
            { key: "reason", header: "Reason" },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Submitted",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Apply for Accommodation">
        <Stack>
          <TextInput
            label="Preferred Room Type"
            placeholder="e.g. Single, Double"
            value={preferredRoomType}
            onChange={(e) => setPreferredRoomType(e.currentTarget.value)}
          />
          <Textarea
            label="Reason"
            placeholder="State your reason or special request"
            value={reason}
            onChange={(e) => setReason(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button loading={submitMutation.isPending} onClick={handleSubmit}>
              Submit
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
