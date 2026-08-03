import { Center, Checkbox, Loader, Table, Text, ThemeIcon } from "@mantine/core";
import type { IconType } from "react-icons";
import { FaInbox } from "react-icons/fa";

export interface Column<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render?: (row: T) => React.ReactNode;
}

export type RowKey = string | number;

export interface Selection<T> {
  selected: Set<RowKey>;
  onChange: (next: Set<RowKey>) => void;
  /** Rows that cannot be acted on — a terminal application, say. They render a
   *  disabled box rather than vanishing, so the count still adds up. */
  isSelectable?: (row: T) => boolean;
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  loading?: boolean;
  minWidth?: number;
  rowKey: (row: T) => RowKey;
  empty: { icon?: IconType; title: string; description?: string };
  /** Omit for a read-only table; the column only appears when passed. */
  selection?: Selection<T>;
}

/** Distilled from the sysadmin client's BatchTable: scroll container, inline
 *  badges, and an EXPLICIT empty state. A bare "No data" is not acceptable. */
export function DataTable<T>({
  rows, columns, loading, minWidth = 760, rowKey, empty, selection,
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

  const selectable = selection
    ? rows.filter((r) => selection.isSelectable?.(r) ?? true)
    : [];
  const selectedHere = selection
    ? selectable.filter((r) => selection.selected.has(rowKey(r))).length
    : 0;
  const allSelected = selectable.length > 0 && selectedHere === selectable.length;

  function toggleAll() {
    if (!selection) return;
    // Only ever touches the rows on screen, so changing a filter cannot
    // silently drop a selection made elsewhere.
    const next = new Set(selection.selected);
    for (const row of selectable) {
      if (allSelected) next.delete(rowKey(row));
      else next.add(rowKey(row));
    }
    selection.onChange(next);
  }

  function toggleOne(key: RowKey) {
    if (!selection) return;
    const next = new Set(selection.selected);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    selection.onChange(next);
  }

  return (
    <Table.ScrollContainer minWidth={minWidth}>
      <Table>
        <Table.Thead>
          <Table.Tr>
            {selection && (
              <Table.Th w={40}>
                <Checkbox
                  aria-label="Select all on this page"
                  checked={allSelected}
                  indeterminate={selectedHere > 0 && !allSelected}
                  onChange={toggleAll}
                  disabled={!selectable.length}
                />
              </Table.Th>
            )}
            {columns.map((c) => (
              <Table.Th key={c.key} ta={c.align ?? "left"}>{c.header}</Table.Th>
            ))}
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {rows.map((row) => {
            const key = rowKey(row);
            const canSelect = selection?.isSelectable?.(row) ?? true;
            return (
              <Table.Tr
                key={key}
                bg={selection?.selected.has(key)
                  ? "var(--mantine-color-blue-0)" : undefined}
              >
                {selection && (
                  <Table.Td>
                    <Checkbox
                      aria-label="Select row"
                      checked={selection.selected.has(key)}
                      onChange={() => toggleOne(key)}
                      disabled={!canSelect}
                    />
                  </Table.Td>
                )}
                {columns.map((c) => (
                  <Table.Td key={c.key} ta={c.align ?? "left"}>
                    {c.render
                      ? c.render(row)
                      : String((row as Record<string, unknown>)[c.key] ?? "—")}
                  </Table.Td>
                ))}
              </Table.Tr>
            );
          })}
        </Table.Tbody>
      </Table>
    </Table.ScrollContainer>
  );
}
