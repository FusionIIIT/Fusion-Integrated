import { Center, Loader, Table, Text, ThemeIcon } from "@mantine/core";
import type { IconType } from "react-icons";
import { FaInbox } from "react-icons/fa";

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render?: (row: T) => React.ReactNode;
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  loading?: boolean;
  minWidth?: number;
  rowKey: (row: T) => string | number;
  empty: { icon?: IconType; title: string; description?: string };
}

/** Distilled from the sysadmin client's BatchTable: scroll container, inline
 *  badges, and an EXPLICIT empty state. A bare "No data" is not acceptable. */
export function DataTable<T>({
  rows, columns, loading, minWidth = 760, rowKey, empty,
}: Props<T>) {
  if (loading) return <Center py="xl"><Loader size="sm" /></Center>;

  if (!rows.length) {
    const Icon = empty.icon ?? FaInbox;
    return (
      <Center py={48}>
        <div style={{ textAlign: "center" }}>
          <ThemeIcon size={48} radius="xl" variant="light" color="gray">
            <Icon size={20} />
          </ThemeIcon>
          <Text fw={600} mt="md">{empty.title}</Text>
          {empty.description && (
            <Text c="dimmed" size="sm" mt={4}>{empty.description}</Text>
          )}
        </div>
      </Center>
    );
  }

  return (
    <Table.ScrollContainer minWidth={minWidth}>
      <Table>
        <Table.Thead>
          <Table.Tr>
            {columns.map((c) => (
              <Table.Th key={c.key} ta={c.align ?? "left"}>{c.header}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row) => (
            <Table.Tr key={rowKey(row)}>
              {columns.map((c) => (
                <Table.Td key={c.key} ta={c.align ?? "left"}>
                  {c.render
                    ? c.render(row)
                    : String((row as Record<string, unknown>)[c.key] ?? "—")}
                </Table.Td>
              ))}
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
