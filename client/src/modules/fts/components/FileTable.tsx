import { Badge, Table, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import type { FileSummary } from "../api/types";

export function FileTable({ files, emptyText }: { files: FileSummary[]; emptyText: string }) {
  if (files.length === 0) {
    return <Text>{emptyText}</Text>;
  }

  return (
    <Table>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Subject</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Owner</Table.Th>
          <Table.Th>Current holder</Table.Th>
          <Table.Th>Updated</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {files.map((file) => (
          <Table.Tr key={file.id}>
            <Table.Td>
              <Link to={`/fts/files/${file.id}`}>{file.subject}</Link>
            </Table.Td>
            <Table.Td>
              <Badge color={file.status === "draft" ? "green" : "red"}>{file.status}</Badge>
              {file.status === "archived" && <Badge color="gray">Read-only</Badge>}
            </Table.Td>
            <Table.Td>{file.owner_name}</Table.Td>
            <Table.Td>{file.holder_name ? file.holder_name : "-"}</Table.Td>
            <Table.Td>{file.updated_at.toLocaleString()}</Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

export default FileTable;
