/* eslint-disable react/prop-types */
import React, { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Container,
  Paper,
  Title,
  Text,
  Button,
  Badge,
  Checkbox,
  Table,
  ScrollArea,
  Flex,
  Tooltip,
  Loader,
  Center,
  Modal,
  Divider,
  ActionIcon,
  Group,
  Timeline,
  ThemeIcon,
  Alert,
} from "@mantine/core";
import {
  FaTrash,
  FaUpload,
  FaDatabase,
  FaSync,
  FaCheckCircle,
  FaTimesCircle,
  FaHistory,
  FaExclamationTriangle,
} from "react-icons/fa";
import { showNotification } from "@mantine/notifications";
import {
  fetchDatabases,
  fetchBackups,
  createBackup,
  deleteBackup as apiDeleteBackup,
  getBackupStatus,
  fetchRestores,
  getRestoreStatus,
} from "../../api/Backups";
import PageHeader from "../../components/PageHeader/PageHeader";

// ── helpers ────────────────────────────────────────────────────────────────────

const fmtDate = (iso) => {
  const d = new Date(iso);
  return {
    date: d.toLocaleDateString("en-US", {
      month: "2-digit",
      day: "2-digit",
      year: "numeric",
    }),
    time: d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    }),
    relative: relativeTime(d),
  };
};

const relativeTime = (d) => {
  const diff = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
  return `${Math.floor(diff / 86400)} days ago`;
};

const fmtBytes = (bytes) => {
  if (!bytes || bytes <= 0) return "—";
  if (bytes >= 1e9) return (bytes / 1e9).toFixed(2) + " GB";
  if (bytes >= 1e6) return (bytes / 1e6).toFixed(2) + " MB";
  return (bytes / 1e3).toFixed(2) + " KB";
};

const fmtDuration = (ms) => {
  if (!ms || ms <= 0) return "—";
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}m ${s % 60}s` : `${s}s`;
};

// ── sub-components ─────────────────────────────────────────────────────────────

const StatusBadge = ({ status }) => {
  if (status === "in_progress")
    return (
      <Group spacing={6}>
        <Loader size={14} color="blue" />
        <Text size="sm" color="blue" fw={500}>
          In progress
        </Text>
      </Group>
    );
  if (status === "success")
    return (
      <Badge color="green" variant="light" radius="sm">
        Successful
      </Badge>
    );
  return (
    <Badge color="red" variant="light" radius="sm">
      Failed
    </Badge>
  );
};

const BackupHeatmap = ({ backups }) => {
  // Take last 90 backups, oldest first
  const grid = React.useMemo(() => {
    const last90 = [...backups].slice(0, 90).reverse();
    // Pad to 90 if fewer than 90
    const padded = Array.from({ length: 90 }, (_, i) => {
      const b = last90[i];
      if (!b) return { status: "none", label: "No backup" };
      const d = new Date(b.created_at);
      const dateStr = d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
      const timeStr = d.toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      });
      const size = b.size_bytes > 0 ? fmtBytes(b.size_bytes) : null;
      const dur = b.duration_ms > 0 ? fmtDuration(b.duration_ms) : null;
      const label =
        b.status === "success"
          ? `${dateStr} ${timeStr} — ${size ?? "?"}${dur ? `, ${dur}` : ""}`
          : b.status === "failed"
            ? `${dateStr} ${timeStr} — Failed: ${b.error_message || "unknown error"}`
            : `${dateStr} ${timeStr} — In progress`;
      return { status: b.status, label };
    });
    return padded;
  }, [backups]);

  return (
    <Box
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(30, 1fr)",
        gap: 4,
      }}
    >
      {grid.map((cell, i) => (
        <Tooltip
          key={i}
          label={cell.label}
          withArrow
          position="top"
          multiline
          maw={260}
        >
          <Box
            style={{
              aspectRatio: "1 / 1",
              borderRadius: 4,
              backgroundColor:
                cell.status === "success"
                  ? "#2f9e44"
                  : cell.status === "failed"
                    ? "#e03131"
                    : cell.status === "in_progress"
                      ? "#1971c2"
                      : "#343a40",
              cursor: "default",
              transition: "opacity 0.15s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.opacity = "0.7")}
            onMouseLeave={(e) => (e.currentTarget.style.opacity = "1")}
          />
        </Tooltip>
      ))}
    </Box>
  );
};

// ── main page ──────────────────────────────────────────────────────────────────

const BackupPage = () => {
  const navigate = useNavigate();
  const [databases, setDatabases] = useState([]);
  const [selectedDb, setSelectedDb] = useState(null);
  const [backups, setBackups] = useState([]);
  const [restores, setRestores] = useState([]);
  const [loadingDbs, setLoadingDbs] = useState(true);
  const [loadingBackups, setLoadingBackups] = useState(false);
  const [loadingRestores, setLoadingRestores] = useState(false);
  const [makingBackup, setMakingBackup] = useState(false);
  const [deleteModal, setDeleteModal] = useState({ open: false, id: null });
  const [restoreModal, setRestoreModal] = useState({ open: false, id: null });
  const [deleting, setDeleting] = useState(false);
  const [selected, setSelected] = useState(() => new Set());
  const [bulkDeleteModal, setBulkDeleteModal] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const pollTimerRef = useRef(null);
  const restorePollTimerRef = useRef(null);

  // ── load databases ──
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoadingDbs(true);
      try {
        const dbs = await fetchDatabases();
        if (!cancelled) {
          setDatabases(Array.isArray(dbs) ? dbs : []);
          if (dbs.length > 0 && !selectedDb) {
            setSelectedDb(dbs[0].id);
          }
        }
      } catch {
        if (!cancelled) setDatabases([]);
      } finally {
        if (!cancelled) setLoadingDbs(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── load backups when db changes ──
  const loadBackups = useCallback(async () => {
    if (!selectedDb) return;
    setLoadingBackups(true);
    try {
      const data = await fetchBackups(selectedDb);
      setBackups(Array.isArray(data) ? data : []);
      setSelected(new Set());
    } catch {
      setBackups([]);
    } finally {
      setLoadingBackups(false);
    }
  }, [selectedDb]);

  useEffect(() => {
    loadBackups();
  }, [loadBackups]);

  // ── load restores when db changes ──
  const loadRestores = useCallback(async () => {
    if (!selectedDb) return;
    setLoadingRestores(true);
    try {
      const data = await fetchRestores(selectedDb);
      setRestores(Array.isArray(data) ? data : []);
    } catch {
      setRestores([]);
    } finally {
      setLoadingRestores(false);
    }
  }, [selectedDb]);

  useEffect(() => {
    loadRestores();
  }, [loadRestores]);

  // ── poll in-progress restores ──
  useEffect(() => {
    if (restorePollTimerRef.current) {
      clearInterval(restorePollTimerRef.current);
      restorePollTimerRef.current = null;
    }

    const inProgress = restores.filter((r) => r.status === "in_progress");
    if (inProgress.length === 0) return;

    restorePollTimerRef.current = setInterval(async () => {
      let anyChanged = false;
      const updated = [...restores];

      for (const rr of inProgress) {
        try {
          const fresh = await getRestoreStatus(rr.id);
          if (fresh.status !== "in_progress") {
            anyChanged = true;
            const idx = updated.findIndex((r) => r.id === rr.id);
            if (idx !== -1) updated[idx] = fresh;

            if (fresh.status === "success") {
              showNotification({
                title: "Restore complete",
                message: `Database restored successfully in ${fmtDuration(fresh.duration_ms)}.`,
                color: "green",
                position: "top-center",
                autoClose: 8000,
              });
              // reload db info to refresh sidebar stats
              loadBackups();
            } else if (fresh.status === "failed") {
              showNotification({
                title: "Restore failed",
                message: fresh.error_message || "An unknown error occurred.",
                color: "red",
                position: "top-center",
                autoClose: 8000,
              });
            }
          }
        } catch {
          // ignore poll errors
        }
      }

      if (anyChanged) {
        setRestores(updated);
      }
    }, 3000);

    return () => {
      if (restorePollTimerRef.current) {
        clearInterval(restorePollTimerRef.current);
        restorePollTimerRef.current = null;
      }
    };
  }, [restores, loadBackups]);

  // ── poll in-progress backups ──
  useEffect(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }

    const inProgress = backups.filter((b) => b.status === "in_progress");
    if (inProgress.length === 0) return;

    pollTimerRef.current = setInterval(async () => {
      let anyChanged = false;
      const updated = [...backups];

      for (const bp of inProgress) {
        try {
          const fresh = await getBackupStatus(bp.id);
          if (fresh.status !== "in_progress") {
            anyChanged = true;
            const idx = updated.findIndex((b) => b.id === bp.id);
            if (idx !== -1) updated[idx] = fresh;

            if (fresh.status === "success") {
              showNotification({
                title: "Backup complete",
                message: `Backup finished in ${fmtDuration(fresh.duration_ms)} — ${fmtBytes(fresh.size_bytes)}`,
                color: "green",
                position: "top-center",
              });
            } else if (fresh.status === "failed") {
              showNotification({
                title: "Backup failed",
                message: fresh.error_message || "An unknown error occurred.",
                color: "red",
                position: "top-center",
              });
            }
          }
        } catch {
          // ignore poll errors
        }
      }

      if (anyChanged) {
        setBackups(updated);
      }
    }, 3000);

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [backups]);

  // ── actions ──────────────────────────────────────────────────────────────────

  const handleMakeBackup = async () => {
    setMakingBackup(true);
    try {
      const newBackup = await createBackup(selectedDb);
      setBackups((prev) => [newBackup, ...prev]);
      showNotification({
        title: "Backup started",
        message: "A new backup is now in progress.",
        color: "blue",
        position: "top-center",
      });
    } catch (err) {
      showNotification({
        title: "Error",
        message: err.response?.data?.error || "Failed to start backup.",
        color: "red",
        position: "top-center",
      });
    } finally {
      setMakingBackup(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await apiDeleteBackup(deleteModal.id);
      setBackups((prev) => prev.filter((b) => b.id !== deleteModal.id));
      setSelected((prev) => {
        const next = new Set(prev);
        next.delete(deleteModal.id);
        return next;
      });
      showNotification({
        title: "Backup deleted",
        message: "The backup has been removed.",
        color: "red",
        position: "top-center",
      });
    } catch (err) {
      showNotification({
        title: "Error",
        message: err.response?.data?.error || "Failed to delete backup.",
        color: "red",
        position: "top-center",
      });
    } finally {
      setDeleting(false);
      setDeleteModal({ open: false, id: null });
    }
  };

  const toggleSelected = (id) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const selectableIds = backups
    .filter((b) => b.status !== "in_progress")
    .map((b) => b.id);
  const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selected.has(id));
  const someSelected = selectableIds.some((id) => selected.has(id));

  const toggleSelectAll = () =>
    setSelected(allSelected ? new Set() : new Set(selectableIds));

  const handleBulkDelete = async () => {
    setBulkDeleting(true);
    const ids = [...selected];
    const results = await Promise.allSettled(ids.map((id) => apiDeleteBackup(id)));
    const deletedIds = ids.filter((_, i) => results[i].status === "fulfilled");
    const failed = ids.length - deletedIds.length;
    setBackups((prev) => prev.filter((b) => !deletedIds.includes(b.id)));
    setSelected(new Set());
    setBulkDeleting(false);
    setBulkDeleteModal(false);
    showNotification({
      title: failed ? "Partly deleted" : "Backups deleted",
      message: `${deletedIds.length} backup${deletedIds.length === 1 ? "" : "s"} deleted${failed ? `, ${failed} failed` : ""}.`,
      color: failed ? "yellow" : "red",
      position: "top-center",
    });
  };

  const handleRestore = () => {
    // BADMS requires approval before any restore is executed. Do not call the
    // direct restore endpoint from this screen; create an approval request.
    const backupId = restoreModal.id;
    setRestoreModal({ open: false, id: null });
    navigate("/badms/restore-requests", { state: { backupId } });
  };

  // ── render ───────────────────────────────────────────────────────────────────

  if (loadingDbs) {
    return (
      <Center h="60vh">
        <Loader size="lg" color="blue" />
      </Center>
    );
  }

  return (
    <Container size="xl">
      <PageHeader title="Backup Management" />

      <Flex gap="xl" align="flex-start" wrap="wrap">
        {/* ── Left panel: database list ── */}
        <Paper
          shadow="md"
          radius="lg"
          p="md"
          withBorder
          style={{ minWidth: 230, flex: "0 0 230px" }}
        >
          <Title order={5} mb="md" color="dimmed">
            Databases
          </Title>

          {databases.length === 0 && (
            <Text size="sm" color="dimmed" ta="center" py="md">
              No databases found.
            </Text>
          )}

          {databases.map((db) => (
            <Paper
              key={db.id}
              radius="md"
              p="sm"
              mb="sm"
              withBorder
              onClick={() => setSelectedDb(db.id)}
              style={{
                cursor: "pointer",
                borderColor:
                  selectedDb === db.id
                    ? "#228be6"
                    : "var(--mantine-color-gray-3)",
                backgroundColor:
                  selectedDb === db.id
                    ? "var(--mantine-color-blue-0)"
                    : undefined,
                transition: "all 0.2s",
              }}
            >
              <Flex justify="space-between" align="flex-start" gap={4}>
                <Text fw={600} size="sm" style={{ lineHeight: 1.3 }}>
                  {db.name}
                </Text>
                <Badge
                  color={db.status === "online" ? "green" : "red"}
                  variant="dot"
                  size="sm"
                  mt={2}
                >
                  {db.status === "online" ? "Online" : "Offline"}
                </Badge>
              </Flex>
              {db.size_bytes && (
                <Text size="xs" color="dimmed" mt={2}>
                  Size: {fmtBytes(db.size_bytes)}
                </Text>
              )}
              <Text size="xs" color="dimmed" mt={2}>
                {db.last_backup_at
                  ? `Last backup ${relativeTime(new Date(db.last_backup_at))}`
                  : "No backups yet"}
              </Text>
              <Text size="xs" color="dimmed">
                {db.backup_count || 0} backup
                {db.backup_count !== 1 ? "s" : ""}
              </Text>
            </Paper>
          ))}
        </Paper>

        {/* ── Right panel ── */}
        <Box style={{ flex: 1, minWidth: 0, maxWidth: "100%" }}>
          {/* Backup Heatmap */}
          <Paper shadow="md" radius="lg" p="lg" withBorder mb="xl">
            <Flex justify="space-between" align="center" mb="xs">
              <Title order={4}>
                Backup History
                <Text span size="xs" color="dimmed" ml="sm">
                  (last {Math.min(backups.length, 90)} backups)
                </Text>
              </Title>
              <Group spacing={6}>
                <Box style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Box
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 2,
                      backgroundColor: "#2f9e44",
                    }}
                  />
                  <Text size="xs" color="dimmed">
                    Success
                  </Text>
                </Box>
                <Box style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Box
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 2,
                      backgroundColor: "#e03131",
                    }}
                  />
                  <Text size="xs" color="dimmed">
                    Failed
                  </Text>
                </Box>
                <Box style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Box
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 2,
                      backgroundColor: "#1971c2",
                    }}
                  />
                  <Text size="xs" color="dimmed">
                    In progress
                  </Text>
                </Box>
                <Box style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Box
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: 2,
                      backgroundColor: "#343a40",
                    }}
                  />
                  <Text size="xs" color="dimmed">
                    No backup
                  </Text>
                </Box>
              </Group>
            </Flex>

            {loadingBackups ? (
              <Center h={60}>
                <Loader size="sm" color="blue" />
              </Center>
            ) : (
              <BackupHeatmap backups={backups} />
            )}
          </Paper>

          {/* Restore Activity Log */}
          <Paper shadow="md" radius="lg" p="lg" withBorder mb="xl">
            <Flex justify="space-between" align="center" mb="md">
              <Flex align="center" gap="sm">
                <FaHistory size={16} color="#228be6" />
                <Title order={4}>Restore History</Title>
              </Flex>
              <Tooltip label="Refresh" withArrow>
                <ActionIcon
                  variant="subtle"
                  color="gray"
                  onClick={loadRestores}
                  loading={loadingRestores}
                >
                  <FaSync size={12} />
                </ActionIcon>
              </Tooltip>
            </Flex>

            <Divider mb="md" />

            {loadingRestores ? (
              <Center h={80}>
                <Loader size="sm" color="blue" />
              </Center>
            ) : restores.length === 0 ? (
              <Text size="sm" color="dimmed" ta="center" py="md">
                No restores performed yet.
              </Text>
            ) : (
              <ScrollArea mah={280}>
                <Timeline active={-1} bulletSize={28} lineWidth={2}>
                  {restores.map((r) => {
                    const isOk = r.status === "success";
                    const isFail = r.status === "failed";
                    const isRunning = r.status === "in_progress";
                    const srcDate = r.source_backup_created_at
                      ? fmtDate(r.source_backup_created_at)
                      : null;
                    const startedFmt = fmtDate(r.started_at);

                    return (
                      <Timeline.Item
                        key={r.id}
                        bullet={
                          <ThemeIcon
                            size={22}
                            radius="xl"
                            color={isOk ? "green" : isFail ? "red" : "blue"}
                          >
                            {isRunning ? (
                              <Loader size={12} color="white" />
                            ) : isOk ? (
                              <FaCheckCircle size={11} />
                            ) : (
                              <FaTimesCircle size={11} />
                            )}
                          </ThemeIcon>
                        }
                        title={
                          <Flex align="center" gap={8}>
                            <Text size="sm" fw={600}>
                              {isRunning
                                ? "Restore in progress…"
                                : isOk
                                  ? "Restore successful"
                                  : "Restore failed"}
                            </Text>
                            <Badge
                              size="xs"
                              color={isOk ? "green" : isFail ? "red" : "blue"}
                              variant="light"
                            >
                              {r.status}
                            </Badge>
                          </Flex>
                        }
                      >
                        <Text size="xs" color="dimmed">
                          Started: {startedFmt.date} {startedFmt.time} (
                          {startedFmt.relative})
                        </Text>
                        {srcDate && (
                          <Text size="xs" color="dimmed">
                            Restored from backup: {srcDate.date} {srcDate.time}
                          </Text>
                        )}
                        {!isRunning && r.duration_ms > 0 && (
                          <Text size="xs" color="dimmed">
                            Duration: {fmtDuration(r.duration_ms)}
                          </Text>
                        )}
                        {isFail && r.error_message && (
                          <Alert
                            icon={<FaExclamationTriangle size={12} />}
                            color="red"
                            variant="light"
                            mt={6}
                            p={6}
                            radius="sm"
                          >
                            <Text size="xs">{r.error_message}</Text>
                          </Alert>
                        )}
                      </Timeline.Item>
                    );
                  })}
                </Timeline>
              </ScrollArea>
            )}
          </Paper>

          {/* Backups table */}
          <Paper shadow="sm" radius="lg" p="lg" withBorder>
            <Flex justify="space-between" align="center" mb="md" wrap="wrap" gap="sm">
              <Flex align="center" gap="sm">
                <Title order={4}>Backups</Title>
                <Tooltip label="Refresh" withArrow>
                  <ActionIcon
                    variant="subtle"
                    color="gray"
                    onClick={loadBackups}
                    loading={loadingBackups}
                  >
                    <FaSync size={12} />
                  </ActionIcon>
                </Tooltip>
              </Flex>
              <Group gap="sm">
                {selected.size > 0 && (
                  <Button
                    color="red"
                    variant="light"
                    radius="md"
                    leftSection={<FaTrash size={13} />}
                    onClick={() => setBulkDeleteModal(true)}
                  >
                    Delete {selected.size} selected
                  </Button>
                )}
                <Button
                  leftSection={<FaDatabase size={14} />}
                  radius="md"
                  loading={makingBackup}
                  onClick={handleMakeBackup}
                  disabled={!selectedDb}
                >
                  Make backup right now
                </Button>
              </Group>
            </Flex>

            <Divider mb="md" />

            {loadingBackups ? (
              <Center h={200}>
                <Loader size="md" />
              </Center>
            ) : (
              <Table.ScrollContainer minWidth={760}>
                <Table striped highlightOnHover verticalSpacing="sm" horizontalSpacing="md">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th w={40}>
                        <Checkbox
                          aria-label="Select all backups"
                          checked={allSelected}
                          indeterminate={someSelected && !allSelected}
                          onChange={toggleSelectAll}
                          disabled={selectableIds.length === 0}
                        />
                      </Table.Th>
                      <Table.Th>Created at</Table.Th>
                      <Table.Th>Status</Table.Th>
                      <Table.Th>Size</Table.Th>
                      <Table.Th>Duration</Table.Th>
                      <Table.Th>Actions</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {backups.length === 0 && (
                      <Table.Tr>
                        <Table.Td colSpan={6}>
                          <Center py="xl">
                            <Text c="dimmed">
                              No backups yet. Click &quot;Make backup right now&quot; to create one.
                            </Text>
                          </Center>
                        </Table.Td>
                      </Table.Tr>
                    )}
                    {backups.map((b) => {
                      const { date, time, relative } = fmtDate(b.created_at);
                      // System database is backup-only; the backend rejects a
                      // restore of it, so hide the option here too.
                      const dbRestorable =
                        databases.find((d) => d.id === b.db_name)?.restorable !== false;
                      return (
                        <Table.Tr
                          key={b.id}
                          bg={selected.has(b.id) ? "var(--mantine-color-blue-light)" : undefined}
                        >
                          <Table.Td>
                            <Checkbox
                              aria-label="Select backup"
                              checked={selected.has(b.id)}
                              onChange={() => toggleSelected(b.id)}
                              disabled={b.status === "in_progress"}
                            />
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm" fw={500}>
                              {date} {time}
                            </Text>
                            <Text size="xs" c="dimmed">
                              ({relative})
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <StatusBadge status={b.status} />
                            {b.status === "failed" && b.error_message && (
                              <Tooltip label={b.error_message} withArrow multiline maw={300}>
                                <Text size="xs" c="red" style={{ cursor: "help" }}>
                                  hover for details
                                </Text>
                              </Tooltip>
                            )}
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm">{fmtBytes(b.size_bytes)}</Text>
                          </Table.Td>
                          <Table.Td>
                            <Text size="sm">
                              {b.status === "in_progress" ? "—" : fmtDuration(b.duration_ms)}
                            </Text>
                          </Table.Td>
                          <Table.Td>
                            <Group gap={8} wrap="nowrap">
                              <Tooltip label="Delete backup" withArrow>
                                <ActionIcon
                                  color="red"
                                  variant="light"
                                  radius="md"
                                  disabled={b.status === "in_progress"}
                                  onClick={() => setDeleteModal({ open: true, id: b.id })}
                                >
                                  <FaTrash size={14} />
                                </ActionIcon>
                              </Tooltip>
                              <Tooltip
                                label={
                                  dbRestorable
                                    ? "Restore from this backup"
                                    : "This database is backup-only and cannot be restored"
                                }
                                withArrow
                              >
                                <span>
                                  <ActionIcon
                                    color="blue"
                                    variant="light"
                                    radius="md"
                                    disabled={b.status !== "success" || !dbRestorable}
                                    onClick={() => setRestoreModal({ open: true, id: b.id })}
                                  >
                                    <FaUpload size={14} />
                                  </ActionIcon>
                                </span>
                              </Tooltip>
                            </Group>
                          </Table.Td>
                        </Table.Tr>
                      );
                    })}
                  </Table.Tbody>
                </Table>
              </Table.ScrollContainer>
            )}
          </Paper>
        </Box>
      </Flex>

      {/* ── Delete confirm modal ── */}
      <Modal
        opened={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, id: null })}
        title="Delete Backup"
        centered
        radius="md"
      >
        <Text size="sm" mb="xl">
          Are you sure you want to delete this backup? This action cannot be
          undone. The backup file will be permanently removed from disk.
        </Text>
        <Flex justify="space-between">
          <Button
            variant="default"
            onClick={() => setDeleteModal({ open: false, id: null })}
            disabled={deleting}
          >
            Cancel
          </Button>
          <Button color="red" onClick={handleDelete} loading={deleting}>
            Delete
          </Button>
        </Flex>
      </Modal>

      {/* ── Bulk delete confirm modal ── */}
      <Modal
        opened={bulkDeleteModal}
        onClose={() => setBulkDeleteModal(false)}
        title="Delete selected backups"
        centered
        radius="md"
      >
        <Text size="sm" mb="xl">
          Are you sure you want to delete <strong>{selected.size}</strong> selected backup
          {selected.size === 1 ? "" : "s"}? This action cannot be undone — the backup files
          will be permanently removed from disk.
        </Text>
        <Flex justify="space-between">
          <Button variant="default" onClick={() => setBulkDeleteModal(false)} disabled={bulkDeleting}>
            Cancel
          </Button>
          <Button color="red" onClick={handleBulkDelete} loading={bulkDeleting}>
            Delete {selected.size}
          </Button>
        </Flex>
      </Modal>

      {/* ── Restore confirm modal ── */}
      <Modal
        opened={restoreModal.open}
        onClose={() => setRestoreModal({ open: false, id: null })}
        title="Restore Database"
        centered
        radius="md"
      >
        <Text size="sm" mb="md">
          This will take you to the BADMS restoration request form. The restore
          will not execute until the required approvals have been completed.
        </Text>
        <Text size="sm" fw={600} color="orange" mb="xl">
          Do not restore directly from this screen. The approval workflow must
          be completed before the database is changed.
        </Text>
        <Flex justify="space-between">
          <Button
            variant="default"
            onClick={() => setRestoreModal({ open: false, id: null })}
          >
            Cancel
          </Button>
          <Button color="blue" onClick={handleRestore}>
            Continue to request
          </Button>
        </Flex>
      </Modal>
    </Container>
  );
};

export default BackupPage;
