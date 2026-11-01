/* eslint-disable react/prop-types */
import { useMemo, useState } from "react";
import { Button, Card, Grid, Group, NumberInput, Select, Stack, Text, Textarea, TextInput, ThemeIcon } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { addSingleStudent } from "../../../api/UpcomingBatches";
import { EMPTY_MANUAL_FORM, MANUAL_SECTIONS, SECTION_META } from "../config/studentFields";
import { SPECIALIZATION_OPTIONS } from "../config/programmeConfig";

const toDateString = (value) => {
  if (!value) return "";
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString().slice(0, 10);
};

const ManualEntryForm = ({ config, academicYear, onSubmitted, onCancel }) => {
  const [form, setForm] = useState(EMPTY_MANUAL_FORM);
  const [submitting, setSubmitting] = useState(false);

  const disciplineOptions = useMemo(() => [...new Set(Object.values(config.disciplineMap).flat())], [config]);
  const setField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const renderField = (field) => {
    if (field.specializationOnly && !config.showSpecialization) return null;
    if (field.visibleWhen && !field.visibleWhen(form)) return null;

    const common = { label: field.label, required: field.required, size: "sm", radius: "md" };
    let input;
    if (field.type === "textarea") {
      input = <Textarea {...common} autosize minRows={2} value={form[field.key] ?? ""} onChange={(e) => setField(field.key, e.currentTarget.value)} />;
    } else if (field.type === "number") {
      input = <NumberInput {...common} hideControls value={form[field.key] ?? ""} onChange={(v) => setField(field.key, v)} />;
    } else if (field.type === "date") {
      input = <DateInput {...common} clearable value={form[field.key] || null} valueFormat="YYYY-MM-DD" onChange={(v) => setField(field.key, v)} />;
    } else if (field.type === "select") {
      input = <Select {...common} clearable searchable data={field.options} value={form[field.key] || null} onChange={(v) => setField(field.key, v)} />;
    } else if (field.type === "discipline") {
      input = <Select {...common} searchable data={disciplineOptions} value={form[field.key] || null} onChange={(v) => setField(field.key, v)} />;
    } else if (field.type === "specialization") {
      input = <Select {...common} searchable clearable data={SPECIALIZATION_OPTIONS} value={form[field.key] || null} onChange={(v) => setField(field.key, v)} />;
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
    const missing = MANUAL_SECTIONS.flatMap((s) => s.fields).filter(
      (f) => f.required && !(f.specializationOnly && !config.showSpecialization) && !String(form[f.key] ?? "").trim(),
    );
    if (missing.length) {
      notifications.show({ title: "Missing fields", message: `Fill: ${missing.map((f) => f.label).join(", ")}`, color: "red" });
      return;
    }

    setSubmitting(true);
    try {
      const res = await addSingleStudent({
        ...form,
        dob: toDateString(form.dob),
        programme_type: config.programmeType,
        academic_year: academicYear,
      });
      if (res.success) {
        notifications.show({ title: "Success", message: res.message, color: "green" });
        setForm(EMPTY_MANUAL_FORM);
        onSubmitted?.();
      } else {
        notifications.show({ title: "Error", message: res.message, color: "red" });
      }
    } catch (error) {
      notifications.show({ title: "Error", message: error.response?.data?.message || "Failed to add student.", color: "red" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Stack gap="md">
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
            <Grid gutter="md">{section.fields.map(renderField)}</Grid>
          </Card>
        );
      })}
      <Text size="xs" c="dimmed">
        Batch is derived from the discipline and category. A matching running batch must exist for the selected year.
      </Text>
      <Group justify="flex-end">
        <Button variant="default" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} loading={submitting}>
          Add Student
        </Button>
      </Group>
    </Stack>
  );
};

export default ManualEntryForm;
