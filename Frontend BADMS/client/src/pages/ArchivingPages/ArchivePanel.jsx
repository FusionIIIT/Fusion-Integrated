/* eslint-disable react/prop-types */
import { useEffect, useMemo, useState } from "react";
import {
  Badge,
  Button,
  Center,
  Checkbox,
  Container,
  Group,
  Loader,
  Modal,
  Pagination,
  Paper,
  Select,
  Table,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { FaArchive, FaSearch, FaUndo, FaUserGraduate } from "react-icons/fa";
import { notifications } from "@mantine/notifications";
import PageHeader from "../../components/PageHeader/PageHeader";
import { archiveUsers, fetchArchiveList, restoreUsers } from "../../api/Archive";

const STATUS_BADGE = {
  PRESENT: { label: "Active", color: "green" },
  ARCHIVED: { label: "Archived", color: "gray" },
  ALUMNI: { label: "Alumni", color: "indigo" },
  LEFT: { label: "Left", color: "orange" },
};

const PAGE_SIZE = 20;

const StatusBadge = ({ status }) => {
  const cfg = STATUS_BADGE[status] || { label: status || "—", color: "gray" };
  return (
    <Badge color={cfg.color} variant="light" radius="sm">
      {cfg.label}
    </Badge>
  );
};

const ArchivePanel = ({ type, title, subtitle, columns, filterKeys }) => {
  const [tab, setTab] = useState("archive");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({});
  const [selected, setSelected] = useState([]);
  const [pending, setPending] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [page, setPage] = useState(1);

  const load = () => {
    setLoading(true);
    setSelected([]);
    fetchArchiveList(type, tab === "archived" ? "archived" : "active")
      .then((data) => setRows(data.results || []))
      .catch(() => notifications.show({ title: "Error", message: "Failed to load records.", color: "red" }))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    setFilters({});
    setSearch("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, tab]);

  const filterOptions = useMemo(() => {
    const opts = {};
    filterKeys.forEach((f) => {
      opts[f.key] = [...new Set(rows.map((r) => r[f.key]).filter((v) => v !== null && v !== undefined && v !== ""))]
        .map(String)
        .sort();
    });
    return opts;
  }, [rows, filterKeys]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    return rows.filter((r) => {
      if (term && !`${r.full_name} ${r.username}`.toLowerCase().includes(term)) return false;
      return filterKeys.every((f) => !filters[f.key] || String(r[f.key]) === String(filters[f.key]));
    });
  }, [rows, search, filters, filterKeys]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paged = useMemo(() => filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), [filtered, page]);

  useEffect(() => {
    setPage(1);
  }, [search, filters, rows]);

  const allVisibleSelected = paged.length > 0 && paged.every((r) => selected.includes(r.username));
  const toggleAll = () =>
    setSelected((prev) => {
      const ids = paged.map((r) => r.username);
      return allVisibleSelected ? prev.filter((u) => !ids.includes(u)) : [...new Set([...prev, ...ids])];
    });
  const toggleOne = (username) =>
    setSelected((prev) => (prev.includes(username) ? prev.filter((u) => u !== username) : [...prev, username]));

  const runAction = async () => {
    setSubmitting(true);
    try {
      const res =
        pending.action === "restore"
          ? await restoreUsers(selected, type)
          : await archiveUsers(selected, type, pending.action);
      if (res.success) {
        notifications.show({ title: "Done", message: res.message, color: "green" });
        setPending(null);
        load();
      } else {
        notifications.show({ title: "Error", message: res.message, color: "red" });
      }
    } catch (error) {
      notifications.show({ title: "Error", message: error.response?.data?.message || "Action failed.", color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  const actionLabel = { archive: "Archive", alumni: "Move to Alumni", restore: "Restore" }[pending?.action] || "";

  return (
    <Container size="xl">
      <PageHeader title={title} subtitle={subtitle} />

      <Paper p="lg" radius="md" withBorder>
        <Tabs value={tab} onChange={setTab} variant="pills" radius="md" keepMounted={false}>
          <Tabs.List mb="md">
            <Tabs.Tab value="archive" leftSection={<FaArchive size={12} />}>
              Active
            </Tabs.Tab>
            <Tabs.Tab value="archived" leftSection={<FaUserGraduate size={12} />}>
              Archived
            </Tabs.Tab>
          </Tabs.List>

          <Group justify="space-between" align="flex-end" wrap="wrap" gap="sm" mb="md">
            <Group gap="sm" wrap="wrap">
              <TextInput
                placeholder="Search name or username"
                leftSection={<FaSearch size={12} />}
                value={search}
                onChange={(e) => setSearch(e.currentTarget.value)}
                w={260}
              />
              {filterKeys.map((f) => (
                <Select
                  key={f.key}
                  placeholder={f.label}
                  data={filterOptions[f.key] || []}
                  value={filters[f.key] || null}
                  onChange={(v) => setFilters((prev) => ({ ...prev, [f.key]: v }))}
                  clearable
                  searchable
                  w={180}
                />
              ))}
            </Group>
            <Group gap="sm">
              {tab === "archive" ? (
                <>
                  <Button
                    color="gray"
                    variant="light"
                    leftSection={<FaArchive size={12} />}
                    disabled={!selected.length}
                    onClick={() => setPending({ action: "archive" })}
                  >
                    Archive ({selected.length})
                  </Button>
                  <Button
                    color="indigo"
                    leftSection={<FaUserGraduate size={12} />}
                    disabled={!selected.length}
                    onClick={() => setPending({ action: "alumni" })}
                  >
                    Alumni ({selected.length})
                  </Button>
                </>
              ) : (
                <Button
                  color="green"
                  leftSection={<FaUndo size={12} />}
                  disabled={!selected.length}
                  onClick={() => setPending({ action: "restore" })}
                >
                  Restore ({selected.length})
                </Button>
              )}
            </Group>
          </Group>

          {loading ? (
            <Center h={200}>
              <Loader />
            </Center>
          ) : filtered.length === 0 ? (
            <Text ta="center" c="dimmed" py="xl">
              No {tab === "archived" ? "archived" : "active"} records.
            </Text>
          ) : (
            <>
              <Text size="sm" c="dimmed" mb="xs">
                {filtered.length} record(s){selected.length ? ` · ${selected.length} selected` : ""}
              </Text>
              <Table.ScrollContainer minWidth={720}>
                <Table highlightOnHover verticalSpacing="sm" stickyHeader>
                  <Table.Thead style={{ background: "var(--mantine-color-gray-0)" }}>
                    <Table.Tr>
                      <Table.Th w={40}>
                        <Checkbox checked={allVisibleSelected} onChange={toggleAll} aria-label="Select all" />
                      </Table.Th>
                      {columns.map((c) => (
                        <Table.Th key={c.key}>{c.label}</Table.Th>
                      ))}
                      <Table.Th>Status</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {paged.map((r) => (
                      <Table.Tr key={r.username} bg={selected.includes(r.username) ? "var(--mantine-color-blue-0)" : undefined}>
                        <Table.Td>
                          <Checkbox
                            checked={selected.includes(r.username)}
                            onChange={() => toggleOne(r.username)}
                            aria-label={`Select ${r.username}`}
                          />
                        </Table.Td>
                        {columns.map((c) => (
                          <Table.Td key={c.key}>{r[c.key] === "" || r[c.key] == null ? "—" : String(r[c.key])}</Table.Td>
                        ))}
                        <Table.Td>
                          <StatusBadge status={r.user_status} />
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
              {pageCount > 1 && (
                <Group justify="center" mt="md">
                  <Pagination total={pageCount} value={page} onChange={setPage} size="sm" radius="md" />
                </Group>
              )}
            </>
          )}
        </Tabs>
      </Paper>

      <Modal opened={!!pending} onClose={() => setPending(null)} title={`${actionLabel} ${selected.length} ${type}(s)`} centered>
        <Text size="sm">
          {pending?.action === "restore"
            ? "This will reactivate the selected accounts (login re-enabled, status set back to Active)."
            : "This will deactivate the selected accounts — they can no longer log in, be promoted, or register for courses. Their records are preserved and this can be undone from the Archived tab."}
        </Text>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={() => setPending(null)}>
            Cancel
          </Button>
          <Button
            color={pending?.action === "restore" ? "green" : "red"}
            loading={submitting}
            onClick={runAction}
          >
            {actionLabel}
          </Button>
        </Group>
      </Modal>
    </Container>
  );
};

export default ArchivePanel;
