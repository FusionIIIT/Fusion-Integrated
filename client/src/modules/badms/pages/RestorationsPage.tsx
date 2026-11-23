import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Stack,
  TextInput,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useCreateRestoration, useRestorations } from "../api/hooks";
import type { RestorationRequest } from "../api/types";

function PlusIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

export default function RestorationsPage() {
  const { data, isPending, error } = useRestorations();
  const createMutation = useCreateRestoration();
  const { can } = useAuth();
  const canCreate = can("badms.restoration.create");

  const [opened, { open, close }] = useDisclosure(false);
  const [archivalRequestId, setArchivalRequestId] = useState<number | string>(1);
  const [targetDestination, setTargetDestination] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!archivalRequestId || !targetDestination) {
      notifications.show({ title: "Validation Error", message: "Please fill in all required fields.", color: "red" });
      return;
    }

    createMutation.mutate(
      {
        archival_request_id: Number(archivalRequestId),
        target_destination: targetDestination,
      },
      {
        onSuccess: () => {
          notifications.show({ title: "Restoration Requested", message: "Data restoration request submitted." });
          close();
          setTargetDestination("");
        },
        onError: (err) => {
          notifications.show({ title: "Request Failed", message: err.message, color: "red" });
        },
      }
    );
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Data Restorations"
        subtitle="Manage point-in-time restoration requests and audit recovery operations"
        action={
          canCreate && (
            <Button leftSection={<PlusIcon />} onClick={open}>
              New Restoration Request
            </Button>
          )
        }
      />
      <Card padding="lg">
        <DataTable<RestorationRequest>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          empty={{ title: "No restorations", description: "No data restoration requests recorded." }}
          columns={[
            { key: "id", header: "ID", render: (r) => r.id },
            { key: "target_destination", header: "Target Destination", render: (r) => r.target_destination },
            { key: "classification", header: "Classification", render: (r) => r.classification },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "approved_by_user_id",
              header: "Approved By",
              render: (r) => (r.approved_by_user_id ? `User ${r.approved_by_user_id}` : "Pending"),
            },
            {
              key: "created_at",
              header: "Requested At",
              render: (r) => new Date(r.created_at).toLocaleString(),
            },
          ]}
        />
      </Card>

      <Modal
        opened={opened}
        onClose={close}
        title="Submit Data Restoration Request"
        size="md"
        withinPortal={false}
        transitionProps={{ duration: 0 }}
      >
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <NumberInput
              label="Archival Request ID"
              required
              min={1}
              value={archivalRequestId}
              onChange={(val) => setArchivalRequestId(val)}
            />
            <TextInput
              label="Target Destination"
              placeholder="/data/recovery/cse/dataset_restored"
              required
              value={targetDestination}
              onChange={(e) => setTargetDestination(e.currentTarget.value)}
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={close}>
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending}>
                Submit Request
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Container>
  );
}
