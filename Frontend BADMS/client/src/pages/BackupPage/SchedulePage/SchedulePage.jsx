/* eslint-disable react/prop-types */
import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Container,
  Paper,
  Title,
  Text,
  Button,
  Badge,
  Flex,
  Loader,
  Center,
  Modal,
  Divider,
  ActionIcon,
  Group,
  Select,
  NumberInput,
  Switch,
  TextInput,
  Table,
  ScrollArea,
  Tooltip,
  Alert,
  Code,
  Stack,
  SegmentedControl,
} from "@mantine/core";
import {
  FaClock,
  FaTrash,
  FaPlay,
  FaPause,
  FaPlus,
  FaSync,
  FaCalendarAlt,
  FaInfoCircle,
  FaExclamationTriangle,
} from "react-icons/fa";
import { showNotification } from "@mantine/notifications";
import {
  fetchSchedules,
  saveSchedule,
  toggleSchedule,
  deleteSchedule,
  previewNextRuns,
  fetchDatabases,
} from "../../../api/Backups";
import PageHeader from "../../../components/PageHeader/PageHeader";

// ── helpers ────────────────────────────────────────────────────────────────────

const pad2 = (n) => String(n).padStart(2, "0");

const fmtDatetime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
};

const relativeTime = (iso) => {
  if (!iso) return null;
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 0) {
    const abs = Math.abs(diff);
    if (abs < 60) return "in a few seconds";
    if (abs < 3600) return `in ${Math.floor(abs / 60)}m`;
    if (abs < 86400) return `in ${Math.floor(abs / 3600)}h`;
    return `in ${Math.floor(abs / 86400)}d`;
  }
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

const DOW_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const HOUR_DATA = Array.from({ length: 24 }, (_, i) => ({
  value: String(i),
  label: `${pad2(i)}:00`,
}));

const MINUTE_DATA = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55].map((m) => ({
  value: String(m),
  label: pad2(m),
}));

const DOW_DATA = DOW_LABELS.map((l, i) => ({ value: String(i), label: l }));

const DOM_DATA = Array.from({ length: 28 }, (_, i) => ({
  value: String(i + 1),
  label: String(i + 1),
}));

// ── empty form state ───────────────────────────────────────────────────────────

const emptyForm = (dbName = "") => ({
  db_name: dbName,
  enabled: true,
  frequency: "daily",
  hour: 2,
  minute: 0,
  day_of_week: 0,
  day_of_month: 1,
  cron_expression: "0 2 * * *",
  retain_last_n: 7,
});

// ── sub-components ─────────────────────────────────────────────────────────────

const FrequencyBadge = ({ frequency, enabled }) => {
  const colors = {
    daily: "blue",
    weekly: "grape",
    monthly: "teal",
    custom: "orange",
  };
  return (
    <Group spacing={4}>
      <Badge color={colors[frequency] ?? "gray"} variant="light" size="sm">
        {frequency}
      </Badge>
      {!enabled && (
        <Badge color="gray" variant="outline" size="sm">
          paused
        </Badge>
      )}
    </Group>
  );
};

const NextRunsPreview = ({ previewData, loading }) => {
  if (loading) {
    return (
      <Center h={60}>
        <Loader size="xs" color="blue" />
      </Center>
    );
  }
  if (!previewData || previewData.length === 0) return null;

  return (
    <Box mt="xs">
      <Text size="xs" color="dimmed" mb={4} fw={500}>
        Next 5 scheduled runs (UTC):
      </Text>
      <Stack spacing={2}>
        {previewData.map((iso, i) => (
          <Flex key={i} align="center" gap={8}>
            <FaCalendarAlt size={10} color="#228be6" />
            <Text size="xs" style={{ fontFamily: "monospace" }}>
              {fmtDatetime(iso)}
            </Text>
          </Flex>
        ))}
      </Stack>
    </Box>
  );
};

// ── schedule form modal ────────────────────────────────────────────────────────

const ScheduleFormModal = ({
  opened,
  onClose,
  onSaved,
  databases,
  editing,
}) => {
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [formError, setFormError] = useState("");

  useEffect(() => {
    if (opened) {
      if (editing) {
        setForm({
          db_name: editing.db_name,
          enabled: editing.enabled,
          frequency: editing.frequency,
          hour: editing.hour,
          minute: editing.minute,
          day_of_week: editing.day_of_week ?? 0,
          day_of_month: editing.day_of_month ?? 1,
          cron_expression: editing.cron_expression || "0 2 * * *",
          retain_last_n: editing.retain_last_n,
        });
      } else {
        setForm(emptyForm(databases[0]?.id || ""));
      }
      setPreviewData(null);
      setFormError("");
    }
  }, [opened, editing, databases]);

  const set = (key, val) => setForm((prev) => ({ ...prev, [key]: val }));

  const handlePreview = async () => {
    setPreviewing(true);
    setFormError("");
    try {
      const res = await previewNextRuns({
        frequency: form.frequency,
        hour: form.hour,
        minute: form.minute,
        day_of_week: form.day_of_week,
        day_of_month: form.day_of_month,
        cron_expression: form.cron_expression,
      });
      setPreviewData(res.next_runs || []);
    } catch (err) {
      setFormError(err.response?.data?.error || "Failed to preview schedule.");
    } finally {
      setPreviewing(false);
    }
  };

  const handleSave = async () => {
    if (!form.db_name) {
      setFormError("Please select a database.");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      const saved = await saveSchedule({
        db_name: form.db_name,
        enabled: form.enabled,
        frequency: form.frequency,
        hour: form.hour,
        minute: form.minute,
        day_of_week: form.frequency === "weekly" ? form.day_of_week : null,
        day_of_month: form.frequency === "monthly" ? form.day_of_month : null,
        cron_expression:
          form.frequency === "custom" ? form.cron_expression : "",
        retain_last_n: form.retain_last_n,
      });
      onSaved(saved);
      onClose();
    } catch (err) {
      setFormError(err.response?.data?.error || "Failed to save schedule.");
    } finally {
      setSaving(false);
    }
  };

  const dbData = databases.map((db) => ({ value: db.id, label: db.name }));

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Flex align="center" gap={8}>
          <FaClock size={16} color="#228be6" />
          <Text fw={600}>
            {editing ? "Edit Backup Schedule" : "New Backup Schedule"}
          </Text>
        </Flex>
      }
      size="lg"
      centered
      radius="md"
    >
      <Stack spacing="md">
        {/* Database */}
        <Select
          label="Database"
          data={dbData}
          value={form.db_name}
          onChange={(v) => set("db_name", v)}
          required
          disabled={!!editing}
          description={
            editing ? "Cannot change database of existing schedule" : undefined
          }
        />

        {/* Enabled toggle */}
        <Flex align="center" justify="space-between">
          <Box>
            <Text size="sm" fw={500}>
              Enable schedule
            </Text>
            <Text size="xs" color="dimmed">
              Disable to pause without deleting
            </Text>
          </Box>
          <Switch
            checked={form.enabled}
            onChange={(e) => set("enabled", e.currentTarget.checked)}
            color="blue"
            size="md"
          />
        </Flex>

        <Divider />

        {/* Frequency */}
        <Box>
          <Text size="sm" fw={500} mb={6}>
            Frequency
          </Text>
          <SegmentedControl
            fullWidth
            value={form.frequency}
            onChange={(v) => {
              set("frequency", v);
              setPreviewData(null);
            }}
            data={[
              { label: "Daily", value: "daily" },
              { label: "Weekly", value: "weekly" },
              { label: "Monthly", value: "monthly" },
              { label: "Custom", value: "custom" },
            ]}
          />
        </Box>

        {/* Time picker — shown for daily / weekly / monthly */}
        {form.frequency !== "custom" && (
          <Flex gap="md">
            <Select
              label="Hour (UTC)"
              data={HOUR_DATA}
              value={String(form.hour)}
              onChange={(v) => set("hour", parseInt(v))}
              style={{ flex: 1 }}
              searchable
            />
            <Select
              label="Minute"
              data={MINUTE_DATA}
              value={String(form.minute)}
              onChange={(v) => set("minute", parseInt(v))}
              style={{ flex: 1 }}
            />
          </Flex>
        )}

        {/* Weekly — day of week */}
        {form.frequency === "weekly" && (
          <Select
            label="Day of week"
            data={DOW_DATA}
            value={String(form.day_of_week)}
            onChange={(v) => set("day_of_week", parseInt(v))}
          />
        )}

        {/* Monthly — day of month */}
        {form.frequency === "monthly" && (
          <Select
            label="Day of month"
            data={DOM_DATA}
            value={String(form.day_of_month)}
            onChange={(v) => set("day_of_month", parseInt(v))}
            description="Maximum 28 to work across all months"
          />
        )}

        {/* Custom cron expression */}
        {form.frequency === "custom" && (
          <Box>
            <TextInput
              label="Cron expression"
              placeholder="minute hour day month weekday"
              value={form.cron_expression}
              onChange={(e) => set("cron_expression", e.currentTarget.value)}
              description="5-field UTC cron — e.g. 0 3 * * 1 = every Monday at 03:00 UTC"
              styles={{ input: { fontFamily: "monospace" } }}
            />
            <Text size="xs" color="dimmed" mt={4}>
              Fields: <Code>minute hour day-of-month month day-of-week</Code>
            </Text>
          </Box>
        )}

        <Divider />

        {/* Retention */}
        <NumberInput
          label="Keep last N backups"
          description="Older successful backups are automatically deleted. Set 0 to keep all."
          value={form.retain_last_n}
          onChange={(v) => set("retain_last_n", v ?? 0)}
          min={0}
          max={100}
        />

        {/* Preview */}
        <Flex justify="flex-end">
          <Button
            variant="light"
            size="xs"
            leftIcon={<FaCalendarAlt size={12} />}
            loading={previewing}
            onClick={handlePreview}
          >
            Preview next runs
          </Button>
        </Flex>

        <NextRunsPreview previewData={previewData} loading={false} />

        {formError && (
          <Alert
            icon={<FaExclamationTriangle size={14} />}
            color="red"
            variant="light"
            radius="sm"
          >
            {formError}
          </Alert>
        )}

        <Flex justify="space-between" mt="sm">
          <Button variant="default" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          <Button
            color="blue"
            onClick={handleSave}
            loading={saving}
            leftIcon={<FaClock size={13} />}
          >
            {editing ? "Save changes" : "Create schedule"}
          </Button>
        </Flex>
      </Stack>
    </Modal>
  );
};

// ── main page ──────────────────────────────────────────────────────────────────

const SchedulePage = () => {
  const [schedules, setSchedules] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formModal, setFormModal] = useState({ open: false, editing: null });
  const [deleteModal, setDeleteModal] = useState({
    open: false,
    id: null,
    dbName: "",
  });
  const [deleting, setDeleting] = useState(false);
  const [togglingId, setTogglingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [dbsRes, schedsRes] = await Promise.all([
        fetchDatabases(),
        fetchSchedules(),
      ]);
      setDatabases(Array.isArray(dbsRes) ? dbsRes : []);
      setSchedules(Array.isArray(schedsRes) ? schedsRes : []);
    } catch {
      setDatabases([]);
      setSchedules([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSaved = (saved) => {
    setSchedules((prev) => {
      const idx = prev.findIndex((s) => s.id === saved.id);
      if (idx !== -1) {
        const next = [...prev];
        next[idx] = saved;
        return next;
      }
      return [saved, ...prev];
    });
    showNotification({
      title: "Schedule saved",
      message: `Backup schedule for ${saved.db_name} has been ${saved.enabled ? "activated" : "saved (paused)"}.`,
      color: "green",
      position: "top-center",
    });
  };

  const handleToggle = async (sched) => {
    setTogglingId(sched.id);
    try {
      const updated = await toggleSchedule(sched.id);
      setSchedules((prev) =>
        prev.map((s) => (s.id === updated.id ? updated : s)),
      );
      showNotification({
        title: updated.enabled ? "Schedule enabled" : "Schedule paused",
        message: `Backups for ${updated.db_name} are now ${updated.enabled ? "active" : "paused"}.`,
        color: updated.enabled ? "green" : "yellow",
        position: "top-center",
      });
    } catch (err) {
      showNotification({
        title: "Error",
        message: err.response?.data?.error || "Failed to toggle schedule.",
        color: "red",
        position: "top-center",
      });
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteSchedule(deleteModal.id);
      setSchedules((prev) => prev.filter((s) => s.id !== deleteModal.id));
      showNotification({
        title: "Schedule deleted",
        message: `Backup schedule for ${deleteModal.dbName} removed.`,
        color: "red",
        position: "top-center",
      });
    } catch (err) {
      showNotification({
        title: "Error",
        message: err.response?.data?.error || "Failed to delete schedule.",
        color: "red",
        position: "top-center",
      });
    } finally {
      setDeleting(false);
      setDeleteModal({ open: false, id: null, dbName: "" });
    }
  };

  const describeSched = (s) => {
    if (s.frequency === "custom") return s.cron_expression || "custom";
    if (s.frequency === "daily")
      return `Every day at ${pad2(s.hour)}:${pad2(s.minute)} UTC`;
    if (s.frequency === "weekly")
      return `Every ${DOW_LABELS[s.day_of_week ?? 0]} at ${pad2(s.hour)}:${pad2(s.minute)} UTC`;
    if (s.frequency === "monthly")
      return `Day ${s.day_of_month ?? 1} of every month at ${pad2(s.hour)}:${pad2(s.minute)} UTC`;
    return s.frequency;
  };

  if (loading) {
    return (
      <Center h="60vh">
        <Loader size="lg" color="blue" />
      </Center>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Backup Schedules"
        action={
          <Group spacing="sm">
            <Tooltip label="Refresh" withArrow>
              <ActionIcon
                variant="subtle"
                color="gray"
                size="lg"
                onClick={load}
                loading={loading}
              >
                <FaSync size={14} />
              </ActionIcon>
            </Tooltip>
            <Button
              leftIcon={<FaPlus size={13} />}
              color="blue"
              radius="md"
              onClick={() => setFormModal({ open: true, editing: null })}
              disabled={databases.length === 0}
            >
              New schedule
            </Button>
          </Group>
        }
      />

      {databases.length === 0 && (
        <Alert
          icon={<FaInfoCircle size={14} />}
          color="yellow"
          variant="light"
          mb="xl"
          radius="md"
        >
          No databases found. Make sure the backend is running and the database
          is reachable.
        </Alert>
      )}

      {/* Schedule list */}
      <Paper shadow="md" radius="lg" p="lg" withBorder>
        <Flex justify="space-between" align="center" mb="md">
          <Title order={4}>Active Schedules</Title>
          <Text size="sm" color="dimmed">
            {schedules.length} schedule{schedules.length !== 1 ? "s" : ""}
          </Text>
        </Flex>

        <Divider mb="md" />

        {schedules.length === 0 ? (
          <Center py="xl">
            <Stack align="center" spacing="xs">
              <FaClock size={32} color="#adb5bd" />
              <Text color="dimmed" size="sm">
                No schedules yet. Click &quot;New schedule&quot; to create one.
              </Text>
            </Stack>
          </Center>
        ) : (
          <ScrollArea>
            <Table highlightOnHover verticalSpacing="md" horizontalSpacing="md">
              <thead>
                <tr>
                  <th>Database</th>
                  <th>Frequency</th>
                  <th>Schedule</th>
                  <th>Retain</th>
                  <th>Last run</th>
                  <th>Next run</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {schedules.map((s) => (
                  <tr key={s.id}>
                    <td>
                      <Text size="sm" fw={600}>
                        {s.db_name}
                      </Text>
                    </td>
                    <td>
                      <FrequencyBadge
                        frequency={s.frequency}
                        enabled={s.enabled}
                      />
                    </td>
                    <td>
                      <Text
                        size="sm"
                        style={
                          s.frequency === "custom"
                            ? { fontFamily: "monospace" }
                            : undefined
                        }
                      >
                        {describeSched(s)}
                      </Text>
                    </td>
                    <td>
                      <Text size="sm">
                        {s.retain_last_n === 0
                          ? "All"
                          : `Last ${s.retain_last_n}`}
                      </Text>
                    </td>
                    <td>
                      <Text size="sm">
                        {s.last_run_at ? fmtDatetime(s.last_run_at) : "Never"}
                      </Text>
                      {s.last_run_at && (
                        <Text size="xs" color="dimmed">
                          {relativeTime(s.last_run_at)}
                        </Text>
                      )}
                    </td>
                    <td>
                      <Text size="sm" color={s.enabled ? "blue" : "dimmed"}>
                        {s.next_run_at ? fmtDatetime(s.next_run_at) : "—"}
                      </Text>
                      {s.next_run_at && s.enabled && (
                        <Text size="xs" color="dimmed">
                          {relativeTime(s.next_run_at)}
                        </Text>
                      )}
                    </td>
                    <td>
                      <Group spacing={6} noWrap>
                        <Tooltip
                          label={
                            s.enabled ? "Pause schedule" : "Enable schedule"
                          }
                          withArrow
                        >
                          <ActionIcon
                            color={s.enabled ? "yellow" : "green"}
                            variant="light"
                            radius="md"
                            loading={togglingId === s.id}
                            onClick={() => handleToggle(s)}
                          >
                            {s.enabled ? (
                              <FaPause size={13} />
                            ) : (
                              <FaPlay size={13} />
                            )}
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Edit schedule" withArrow>
                          <ActionIcon
                            color="blue"
                            variant="light"
                            radius="md"
                            onClick={() =>
                              setFormModal({ open: true, editing: s })
                            }
                          >
                            <FaClock size={13} />
                          </ActionIcon>
                        </Tooltip>
                        <Tooltip label="Delete schedule" withArrow>
                          <ActionIcon
                            color="red"
                            variant="light"
                            radius="md"
                            onClick={() =>
                              setDeleteModal({
                                open: true,
                                id: s.id,
                                dbName: s.db_name,
                              })
                            }
                          >
                            <FaTrash size={13} />
                          </ActionIcon>
                        </Tooltip>
                      </Group>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </ScrollArea>
        )}
      </Paper>

      {/* Info card */}
      <Paper shadow="sm" radius="lg" p="md" withBorder mt="xl">
        <Flex align="flex-start" gap="sm">
          <FaInfoCircle
            size={16}
            color="#228be6"
            style={{ marginTop: 2, flexShrink: 0 }}
          />
          <Stack spacing={4}>
            <Text size="sm" fw={500}>
              How scheduled backups work
            </Text>
            <Text size="xs" color="dimmed">
              Schedules run inside the Django process via APScheduler — no
              external cron daemon needed. All times are in <strong>UTC</strong>
              . Backups are stored in <Code>Backend/backups/</Code> and older
              ones are automatically pruned according to your retention setting.
              If the server is restarted, schedules are re-registered
              automatically from the database.
            </Text>
            <Text size="xs" color="dimmed">
              Custom cron syntax:{" "}
              <Code>minute hour day-of-month month day-of-week</Code> — e.g.{" "}
              <Code>30 4 * * 1-5</Code> = weekdays at 04:30 UTC.
            </Text>
          </Stack>
        </Flex>
      </Paper>

      {/* Form modal */}
      <ScheduleFormModal
        opened={formModal.open}
        onClose={() => setFormModal({ open: false, editing: null })}
        onSaved={handleSaved}
        databases={databases}
        editing={formModal.editing}
      />

      {/* Delete confirm modal */}
      <Modal
        opened={deleteModal.open}
        onClose={() => setDeleteModal({ open: false, id: null, dbName: "" })}
        title="Delete Schedule"
        centered
        radius="md"
      >
        <Text size="sm" mb="md">
          Are you sure you want to delete the backup schedule for{" "}
          <strong>{deleteModal.dbName}</strong>? Automatic backups will stop
          immediately.
        </Text>
        <Text size="sm" color="dimmed" mb="xl">
          Existing backups are not affected.
        </Text>
        <Flex justify="space-between">
          <Button
            variant="default"
            onClick={() =>
              setDeleteModal({ open: false, id: null, dbName: "" })
            }
            disabled={deleting}
          >
            Cancel
          </Button>
          <Button color="red" onClick={handleDelete} loading={deleting}>
            Delete schedule
          </Button>
        </Flex>
      </Modal>
    </Container>
  );
};

export default SchedulePage;
