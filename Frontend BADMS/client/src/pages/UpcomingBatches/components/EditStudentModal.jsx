/* eslint-disable react/prop-types */
import { useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Box,
  Button,
  Card,
  CloseButton,
  Grid,
  Group,
  Modal,
  NumberInput,
  ScrollArea,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
  ThemeIcon,
} from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { updateStudent } from "../../../api/UpcomingBatches";
import { MANUAL_SECTIONS, SECTION_META, studentToForm } from "../config/studentFields";
import { SPECIALIZATION_OPTIONS } from "../config/programmeConfig";

const toDateString = (value) => {
  if (!value) return "";
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString().slice(0, 10);
};

// ERP data uses varied labels (e.g. "MALE", "JoSAA/CSAB Counselling") that may
// not match the canonical option lists. Keep the stored value selectable so it
// always renders instead of showing an empty control.
const withCurrent = (options, current) =>
  current && !options.includes(current) ? [current, ...options] : options;

const initials = (name) =>
  (name || "")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase() || "?";

const EditStudentModal = ({ opened, onClose, student, config, onSaved }) => {
  const [form, setForm] = useState({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (student) setForm(studentToForm(student));
  }, [student]);

  const disciplineOptions = useMemo(
    () => [...new Set(Object.values(config?.disciplineMap || {}).flat())],
    [config],
  );
  const showSpecialization = config?.showSpecialization;
  const setField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const renderField = (field) => {
    if (field.specializationOnly && !showSpecialization) return null;
    if (field.visibleWhen && !field.visibleWhen(form)) return null;

    const common = { label: field.label, required: field.required, size: "sm", radius: "md" };
    let input;
    if (field.type === "textarea") {
      input = (
        <Textarea {...common} autosize minRows={2} value={form[field.key] ?? ""} onChange={(e) => setField(field.key, e.currentTarget.value)} />
      );
    } else if (field.type === "number") {
      input = <NumberInput {...common} hideControls value={form[field.key] ?? ""} onChange={(v) => setField(field.key, v)} />;
    } else if (field.type === "date") {
      input = <DateInput {...common} clearable value={form[field.key] || null} valueFormat="YYYY-MM-DD" onChange={(v) => setField(field.key, v)} />;
    } else if (field.type === "select") {
      input = (
        <Select {...common} searchable clearable data={withCurrent(field.options, form[field.key])} value={form[field.key] || null} onChange={(v) => setField(field.key, v)} />
      );
    } else if (field.type === "discipline") {
      input = (
        <Select {...common} searchable data={withCurrent(disciplineOptions, form.branch)} value={form.branch || null} onChange={(v) => setField("branch", v)} />
      );
    } else if (field.type === "specialization") {
      input = (
        <Select {...common} searchable clearable data={withCurrent(SPECIALIZATION_OPTIONS, form.specialization)} value={form.specialization || null} onChange={(v) => setField("specialization", v)} />
      );
    } else {
      input = <TextInput {...common} value={form[field.key] ?? ""} onChange={(e) => setField(field.key, e.currentTarget.value)} />;
    }
    const span = field.type === "textarea" ? { base: 12 } : { base: 12, sm: 6, md: 4 };
    return (
      <Grid.Col span={span} key={field.key}>
        {input}
      </Grid.Col>
    );
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const res = await updateStudent(student.id, { ...form, dob: toDateString(form.dob) });
      if (res.success) {
        notifications.show({ title: "Saved", message: res.message, color: "green" });
        onSaved?.(res.student);
        onClose();
      } else {
        notifications.show({ title: "Error", message: res.message, color: "red" });
      }
    } catch (error) {
      notifications.show({ title: "Error", message: error.response?.data?.message || "Failed to update student.", color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      size="xl"
      radius="md"
      padding={0}
      withCloseButton={false}
      overlayProps={{ backgroundOpacity: 0.55, blur: 2 }}
    >
      <Box
        p="lg"
        style={{
          background: "linear-gradient(135deg, var(--mantine-color-indigo-7), var(--mantine-color-blue-9))",
          color: "white",
        }}
      >
        <Group justify="space-between" wrap="nowrap">
          <Group wrap="nowrap" gap="md">
            <Avatar
              size={54}
              radius="md"
              styles={{ placeholder: { backgroundColor: "rgba(255,255,255,0.2)", color: "white", fontWeight: 700 } }}
            >
              {initials(student?.name)}
            </Avatar>
            <div>
              <Text fw={700} size="lg" c="white">
                Edit Student
              </Text>
              <Text size="sm" c="rgba(255,255,255,0.85)">
                {student?.name} · {student?.roll_number || "No roll no."}
              </Text>
            </div>
          </Group>
          <CloseButton onClick={onClose} size="lg" c="white" variant="transparent" aria-label="Close" />
        </Group>
      </Box>

      <ScrollArea.Autosize mah="62vh">
        <Stack gap="md" p="lg">
          {MANUAL_SECTIONS.map((section) => {
            const meta = SECTION_META[section.title] || Object.values(SECTION_META)[0];
            return (
              <Card key={section.title} withBorder radius="md" padding="md">
                <Group gap="xs" mb="sm">
                  <ThemeIcon variant="light" color={meta.color} size="md" radius="sm">
                    <meta.icon size={13} />
                  </ThemeIcon>
                  <Text fw={600} size="sm">
                    {section.title}
                  </Text>
                </Group>
                <Grid>{section.fields.map(renderField)}</Grid>
              </Card>
            );
          })}
        </Stack>
      </ScrollArea.Autosize>

      <Group
        justify="flex-end"
        p="md"
        style={{ borderTop: "1px solid var(--mantine-color-gray-3)", background: "var(--mantine-color-body)" }}
      >
        <Button variant="default" onClick={onClose}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} loading={submitting}>
          Save changes
        </Button>
      </Group>
    </Modal>
  );
};

export default EditStudentModal;
