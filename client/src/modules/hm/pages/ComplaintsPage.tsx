import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Textarea,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useComplaints, useSubmitComplaint } from "../api/hooks";
import type { Complaint } from "../api/types";

export default function ComplaintsPage() {
  const { data, isPending, error } = useComplaints();
  const submitMutation = useSubmitComplaint();

  const [modalOpen, setModalOpen] = useState(false);
  const [category, setCategory] = useState("");
  const [description, setDescription] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  function handleSubmit() {
    submitMutation.mutate(
      { category, description },
      {
        onSuccess: () => {
          notifications.show({
            title: "Success",
            message: "Complaint submitted successfully",
            color: "green",
          });
          setModalOpen(false);
          setCategory("");
          setDescription("");
        },
        onError: (err: any) => {
          notifications.show({
            title: "Error",
            message: err?.message || "Failed to submit complaint",
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
          title="Hostel Complaints"
          subtitle="Submit issues and track resolution events"
        />
        <Button onClick={() => setModalOpen(true)}>File Complaint</Button>
      </Group>

      <Card padding="lg">
        <DataTable<Complaint>
          rows={data ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          columns={[
            { key: "id", header: "ID", render: (r) => `#${r.id}` },
            { key: "category", header: "Category" },
            { key: "description", header: "Description" },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "events",
              header: "Events Count",
              render: (r) => r.events?.length ?? 0,
            },
            {
              key: "created_at",
              header: "Reported On",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title="Report an Issue">
        <Stack>
          <TextInput
            label="Category"
            placeholder="e.g. Electrical, Plumbing, Cleaning"
            required
            value={category}
            onChange={(e) => setCategory(e.currentTarget.value)}
          />
          <Textarea
            label="Description"
            placeholder="Provide details about the issue..."
            required
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
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
