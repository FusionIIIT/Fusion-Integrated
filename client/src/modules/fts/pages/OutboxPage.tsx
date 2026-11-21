import { useEffect, useState } from "react";
import { Badge, Container, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ftsApi } from "../api";
import { FileDetailDrawer } from "../components/FileDetailDrawer";
import type { FTSFile, FTSFileDetail } from "../types";

export default function OutboxPage() {
  const [files, setFiles] = useState<FTSFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<FTSFileDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const loadOutbox = async () => {
    setLoading(true);
    try {
      const data = await ftsApi.getOutbox();
      setFiles(data);
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOutbox();
  }, []);

  const handleSelect = async (f: FTSFile) => {
    try {
      const detail = await ftsApi.getFile(f.file_id);
      setSelectedFile(detail);
    } catch (err) {
      notifications.show({ color: "red", message: errorMessage(err) });
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Outbox"
        subtitle="Files you have forwarded or initiated movement on."
      />
      {loading ? (
        <Text size="sm" c="dimmed">
          Loading outbox...
        </Text>
      ) : files.length === 0 ? (
        <Text size="sm" c="dimmed">
          Your outbox is empty.
        </Text>
      ) : (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>File ID</Table.Th>
              <Table.Th>Subject</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Current Holder</Table.Th>
              <Table.Th>Last Updated</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {files.map((f) => (
              <Table.Tr
                key={f.id}
                style={{ cursor: "pointer" }}
                onClick={() => handleSelect(f)}
              >
                <Table.Td fw={600}>{f.file_id}</Table.Td>
                <Table.Td>{f.subject}</Table.Td>
                <Table.Td>
                  <Badge color={f.status === "archived" ? "green" : "blue"}>
                    {f.status}
                  </Badge>
                </Table.Td>
                <Table.Td>User #{f.current_holder_id ?? "None"}</Table.Td>
                <Table.Td>{new Date(f.updated_at).toLocaleString()}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <FileDetailDrawer
        file={selectedFile}
        opened={!!selectedFile}
        onClose={() => setSelectedFile(null)}
        onRefresh={loadOutbox}
      />
    </Container>
  );
}
