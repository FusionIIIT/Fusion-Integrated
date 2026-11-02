import { useState } from "react";
import {
  Anchor, Badge, Button, Card, Container, Group, Select, Stack, Table,
  TagsInput, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../../auth/AuthProvider";
import { errorMessage, http } from "../../lib/http";
import { ErrorState } from "../../ui/components/ErrorState";
import { PageHeader } from "../../ui/components/PageHeader";

interface ArchivalRequest {
  id: number;
  requester_user_id: number;
  department: string;
  file_name: string;
  file_date: string;
  owners: string[];
  file_type: string;
  reason: string;
  attachment_url: string;
  initial_classification: string;
  status: "submitted" | "hod_approved" | "rejected";
  decision_note: string;
  created_at: string;
}

const PERMISSION_SUBMIT = "badms.archival.submit";
const PERMISSION_REVIEW = "badms.archival.review";
const ENDPOINT = "/badms/archival-requests";
const CLASSIFICATIONS = [
  { value: "critical", label: "Critical" },
  { value: "sensitive", label: "Sensitive" },
  { value: "routine", label: "Routine" },
  { value: "archival", label: "Archival" },
];

export default function SecureArchivalPage() {
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const canSubmit = can(PERMISSION_SUBMIT);
  const canReview = can(PERMISSION_REVIEW);
  const [fileName, setFileName] = useState("");
  const [fileDate, setFileDate] = useState("");
  const [owners, setOwners] = useState<string[]>([]);
  const [fileType, setFileType] = useState("");
  const [reason, setReason] = useState("");
  const [attachmentUrl, setAttachmentUrl] = useState("");
  const [classification, setClassification] = useState<string | null>("routine");

  const requests = useQuery({
    queryKey: ["badms", "archival-requests"],
    queryFn: async () => (await http.get<ArchivalRequest[]>(ENDPOINT)).data,
    retry: false,
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["badms"] });
  const submit = useMutation({
    mutationFn: async () => (await http.post<ArchivalRequest>(ENDPOINT, {
      file_name: fileName,
      file_date: fileDate,
      owners,
      file_type: fileType,
      reason,
      attachment_url: attachmentUrl,
      initial_classification: classification,
    })).data,
    onSuccess: () => {
      setFileName("");
      setFileDate("");
      setOwners([]);
      setFileType("");
      setReason("");
      setAttachmentUrl("");
      setClassification("routine");
      notifications.show({
        color: "green",
        title: "Request submitted",
        message: "Your secure archival request is waiting for department review.",
      });
      void refresh();
    },
    onError: (error) => notifications.show({
      color: "red", title: "Could not submit request", message: errorMessage(error),
    }),
  });
  const decide = useMutation({
    mutationFn: async ({ id, decision }: { id: number; decision: "approve" | "reject" }) =>
      (await http.post<ArchivalRequest>(
        `${ENDPOINT}/${id}/decision`, { decision })).data,
    onSuccess: () => {
      notifications.show({
        color: "green", title: "Decision recorded", message: "The request status has been updated.",
      });
      void refresh();
    },
    onError: (error) => notifications.show({
      color: "red", title: "Could not record decision", message: errorMessage(error),
    }),
  });

  if (requests.error) {
    return <Container size="xl"><ErrorState error={requests.error} /></Container>;
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Secure archival"
        subtitle="Submit a request or review requests from your department."
      />

      {canSubmit && (
        <Card withBorder mb="lg" padding="lg">
          <Stack>
            <Text fw={600}>New archival request</Text>
            <TextInput label="File name" required value={fileName}
              onChange={(event) => setFileName(event.currentTarget.value)} />
            <Group grow>
              <TextInput label="File date" type="date" required value={fileDate}
                onChange={(event) => setFileDate(event.currentTarget.value)} />
              <TextInput label="File type" required value={fileType}
                onChange={(event) => setFileType(event.currentTarget.value)} />
            </Group>
            <TagsInput label="Owners" required value={owners} onChange={setOwners}
              placeholder="Enter an owner and press Enter" />
            <Textarea label="Reason" required minRows={2} value={reason}
              onChange={(event) => setReason(event.currentTarget.value)} />
            <TextInput label="Google Drive file link" type="url" required
              value={attachmentUrl}
              onChange={(event) => setAttachmentUrl(event.currentTarget.value)}
              description="Share a file link; folder links are not accepted." />
            <Select label="Initial classification" data={CLASSIFICATIONS}
              value={classification} onChange={setClassification} required />
            <Group justify="flex-end">
              <Button
                onClick={() => submit.mutate()}
                loading={submit.isPending}
                disabled={!fileName.trim() || !fileDate || !owners.length
                  || !fileType.trim() || !reason.trim() || !attachmentUrl.trim()
                  || !classification}
              >
                Submit request
              </Button>
            </Group>
          </Stack>
        </Card>
      )}

      <Card withBorder padding="lg">
        <Stack gap="md">
          <Text fw={600}>{canReview ? "Department requests" : "My requests"}</Text>
          {requests.isPending ? (
            <Text c="dimmed">Loading requests…</Text>
          ) : requests.data?.length ? (
            <Table.ScrollContainer minWidth={900}>
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>File</Table.Th>
                    <Table.Th>Owners</Table.Th>
                    <Table.Th>Classification</Table.Th>
                    <Table.Th>Attachment</Table.Th>
                    <Table.Th>Status</Table.Th>
                    {canReview && <Table.Th>Decision</Table.Th>}
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {requests.data.map((item) => (
                    <Table.Tr key={item.id}>
                      <Table.Td>
                        <Text fw={500}>{item.file_name}</Text>
                        <Text size="xs" c="dimmed">
                          {item.file_type} · {item.file_date} · {item.department}
                        </Text>
                      </Table.Td>
                      <Table.Td>{item.owners.join(", ")}</Table.Td>
                      <Table.Td>{item.initial_classification}</Table.Td>
                      <Table.Td>
                        <Anchor href={item.attachment_url} target="_blank"
                          rel="noopener noreferrer">Open file</Anchor>
                      </Table.Td>
                      <Table.Td>
                        <Badge color={item.status === "rejected" ? "red"
                          : item.status === "hod_approved" ? "green" : "blue"}>
                          {item.status.replace("_", " ")}
                        </Badge>
                      </Table.Td>
                      {canReview && (
                        <Table.Td>
                          {item.status === "submitted" ? (
                            <Group gap="xs" wrap="nowrap">
                              <Button size="xs" color="green"
                                loading={decide.isPending}
                                onClick={() => decide.mutate({
                                  id: item.id, decision: "approve",
                                })}>Approve</Button>
                              <Button size="xs" color="red" variant="light"
                                loading={decide.isPending}
                                onClick={() => decide.mutate({
                                  id: item.id, decision: "reject",
                                })}>Reject</Button>
                            </Group>
                          ) : item.decision_note || "—"}
                        </Table.Td>
                      )}
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </Table.ScrollContainer>
          ) : (
            <Text c="dimmed">No archival requests yet.</Text>
          )}
        </Stack>
      </Card>
    </Container>
  );
}
