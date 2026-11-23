import { Badge, Card, Container, Loader, Table, Text } from "@mantine/core";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useArchivedFiles } from "../api/hooks";
import type { TrackedFileSummary } from "../api/types";

export default function ArchivePage() {
  const { data: files, isPending, error } = useArchivedFiles();

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Archived Files"
        subtitle="Completed institutional files archived by their owners (read-only permanent repository)."
      />

      {isPending && <Loader size="md" />}
      {error && <ErrorState error={error} />}

      {files && (
        <Card withBorder radius="md" p="md">
          {files.length === 0 ? (
            <Text c="dimmed">No archived files found.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>File Number</Table.Th>
                  <Table.Th>Subject</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Creator (Owner)</Table.Th>
                  <Table.Th>Archived At</Table.Th>
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
                      <Badge color="gray" variant="filled">
                        {f.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {f.creator_designation} (#{f.created_by_user_id})
                    </Table.Td>
                    <Table.Td>
                      {f.archived_at ? new Date(f.archived_at).toLocaleString() : "—"}
                    </Table.Td>
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
