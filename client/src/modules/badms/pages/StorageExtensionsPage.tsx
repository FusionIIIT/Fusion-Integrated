import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Stack,
  Textarea,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useCreateStorageExtension, useStorageExtensions } from "../api/hooks";
import type { StorageExtensionRequest } from "../api/types";

function PlusIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

export default function StorageExtensionsPage() {
  const { data, isPending, error } = useStorageExtensions();
  const createMutation = useCreateStorageExtension();
  const { can } = useAuth();
  const canCreate = can("badms.storage.create");

  const [opened, { open, close }] = useDisclosure(false);
  const [extensionGb, setExtensionGb] = useState<number | string>(10);
  const [justification, setJustification] = useState("");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!justification) {
      notifications.show({ title: "Validation Error", message: "Please provide a justification.", color: "red" });
      return;
    }

    const bytes = (Number(extensionGb) || 10) * 1024 * 1024 * 1024;
    createMutation.mutate(
      {
        requested_extension_bytes: bytes,
        justification,
      },
      {
        onSuccess: () => {
          notifications.show({ title: "Extension Requested", message: "Storage extension request submitted." });
          close();
          setJustification("");
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
        title="Storage Extension Requests"
        subtitle="Request quota extensions for departmental backup storage capacity"
        action={
          canCreate && (
            <Button leftSection={<PlusIcon />} onClick={open}>
              Request Extension
            </Button>
          )
        }
      />
      <Card padding="lg">
        <DataTable<StorageExtensionRequest>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          empty={{ title: "No extension requests", description: "No storage quota extension requests found." }}
          columns={[
            { key: "id", header: "ID", render: (r) => r.id },
            { key: "department", header: "Department", render: (r) => r.department },
            {
              key: "current_usage",
              header: "Current Usage",
              render: (r) => `${(r.current_usage_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`,
            },
            {
              key: "requested_extension",
              header: "Extension Requested",
              render: (r) => `${(r.requested_extension_bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`,
            },
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

      <Modal
        opened={opened}
        onClose={close}
        title="Request Storage Quota Extension"
        size="md"
        withinPortal={false}
        transitionProps={{ duration: 0 }}
      >
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <NumberInput
              label="Additional Storage Required (GB)"
              required
              min={1}
              value={extensionGb}
              onChange={(val) => setExtensionGb(val)}
            />
            <Textarea
              label="Business Justification"
              placeholder="Departmental research archive requires additional quota for semester course project backups."
              required
              minRows={3}
              value={justification}
              onChange={(e) => setJustification(e.currentTarget.value)}
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
