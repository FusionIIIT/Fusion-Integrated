import { Badge, Card, Container, Loader, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useInboxFiles } from "../api/hooks";
import type { TrackedFileSummary } from "../api/types";

export default function InboxPage() {
  const { data: files, isPending, error } = useInboxFiles();

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="File Inbox"
        subtitle="Files currently assigned to you awaiting review, action or forward."
      />

      {isPending && <Loader size="md" />}
      {error && <ErrorState error={error} />}

      {files && (
        <Card withBorder radius="md" p="md">
          {files.length === 0 ? (
            <Text c="dimmed">Your inbox is empty.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>File Number</Table.Th>
                  <Table.Th>Subject</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Creator</Table.Th>
                  <Table.Th>Updated At</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {files.map((f: TrackedFileSummary) => (
                  <Table.Tr key={f.id}>
                    <Table.Td>
                      <Text fw={500}>{f.file_number}</Text>
                    </Table.Td>
                    <Table.Td>{f.subject}</Table.Td>
                    <Table.Td>
                      <Badge color="blue" variant="light">
                        {f.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {f.creator_designation} (#{f.created_by_user_id})
                    </Table.Td>
                    <Table.Td>{new Date(f.updated_at).toLocaleString()}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      )}
    </Container>
  );
}
