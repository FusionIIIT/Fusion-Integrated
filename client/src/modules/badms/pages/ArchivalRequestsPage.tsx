import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useArchivalRequests, useCreateArchivalRequest } from "../api/hooks";
import type { ArchivalRequest, DataClassification } from "../api/types";

function PlusIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

export default function ArchivalRequestsPage() {
  const { data, isPending, error } = useArchivalRequests();
  const createMutation = useCreateArchivalRequest();
  const { can } = useAuth();
  const canCreate = can("badms.archival.create");

  const [opened, { open, close }] = useDisclosure(false);
  const [fileName, setFileName] = useState("");
  const [fileType, setFileType] = useState("application/zip");
  const [fileSizeBytes, setFileSizeBytes] = useState<number | string>(1048576);
  const [fileStoragePath, setFileStoragePath] = useState("");
  const [reason, setReason] = useState("");
  const [initialClassification, setInitialClassification] = useState<DataClassification>("Routine");

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!fileName || !fileStoragePath || !reason) {
      notifications.show({ title: "Validation Error", message: "Please fill in all required fields.", color: "red" });
      return;
    }

    createMutation.mutate(
      {
        file_name: fileName,
        file_type: fileType,
        file_size_bytes: Number(fileSizeBytes) || 1048576,
        file_storage_path: fileStoragePath,
        reason,
        initial_classification: initialClassification,
      },
      {
        onSuccess: () => {
          notifications.show({ title: "Request Submitted", message: "Archival request created successfully." });
          close();
          setFileName("");
          setFileStoragePath("");
          setReason("");
        },
        onError: (err) => {
          notifications.show({ title: "Submission Failed", message: err.message, color: "red" });
        },
      }
    );
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Secure Archival Requests"
        subtitle="Submit and track structured departmental dataset archival with retention policies"
        action={
          canCreate && (
            <Button leftSection={<PlusIcon />} onClick={open}>
              New Archival Request
            </Button>
          )
        }
      />
      <Card padding="lg">
        <DataTable<ArchivalRequest>
          rows={data?.results ?? []}
          loading={isPending}
          rowKey={(r) => r.id}
          minWidth={800}
          empty={{ title: "No archival requests", description: "No secure archival requests have been submitted." }}
          columns={[
            { key: "id", header: "ID", render: (r) => r.id },
            { key: "file_name", header: "File Name", render: (r) => r.file_name },
            { key: "department", header: "Department", render: (r) => r.department },
            {
              key: "classification",
              header: "Classification",
              render: (r) => r.authoritative_classification || r.initial_classification || "—",
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Created",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal
        opened={opened}
        onClose={close}
        title="Submit Secure Archival Request"
        size="md"
        withinPortal={false}
        transitionProps={{ duration: 0 }}
      >
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="File Name"
              placeholder="annual_records_2026.zip"
              required
              value={fileName}
              onChange={(e) => setFileName(e.currentTarget.value)}
            />
            <TextInput
              label="File Type"
              placeholder="application/zip"
              required
              value={fileType}
              onChange={(e) => setFileType(e.currentTarget.value)}
            />
            <NumberInput
              label="File Size (Bytes)"
              required
              min={1}
              value={fileSizeBytes}
              onChange={(val) => setFileSizeBytes(val)}
            />
            <TextInput
              label="Storage Path"
              placeholder="/data/archives/cse/2026/records.zip"
              required
              value={fileStoragePath}
              onChange={(e) => setFileStoragePath(e.currentTarget.value)}
            />
            <Select
              label="Initial Classification"
              data={["Routine", "Sensitive", "Critical", "Archival"]}
              value={initialClassification}
              onChange={(val) => setInitialClassification((val as DataClassification) || "Routine")}
            />
            <Textarea
              label="Reason for Archival"
              placeholder="Mandatory regulatory preservation of departmental exam logs"
              required
              minRows={3}
              value={reason}
              onChange={(e) => setReason(e.currentTarget.value)}
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
