/* eslint-disable react/prop-types */
import { useState } from "react";
import { Alert, Button, FileInput, Group, List, Paper, Stack, Table, Text, ThemeIcon } from "@mantine/core";
import { FaDownload, FaFileExcel, FaUpload } from "react-icons/fa";
import { notifications } from "@mantine/notifications";
import { saveStudentsBatch } from "../../../api/UpcomingBatches";
import { downloadTemplate, parseWorkbook } from "../utils/excel";

const PREVIEW_KEYS = ["Institute Roll Number", "Name", "Discipline", "Specialization", "Category"];

const ExcelUploadFlow = ({ config, academicYear, onSaved, onCancel }) => {
  const [rows, setRows] = useState([]);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState(null);

  const handleFile = async (file) => {
    setResult(null);
    if (!file) {
      setRows([]);
      return;
    }
    try {
      const parsed = await parseWorkbook(file);
      setRows(parsed);
      notifications.show({ title: "Parsed", message: `${parsed.length} row(s) read from file.`, color: "blue" });
    } catch {
      setRows([]);
      notifications.show({ title: "Error", message: "Could not read the Excel file.", color: "red" });
    }
  };

  const handleSave = async () => {
    if (!rows.length) {
      notifications.show({ title: "Nothing to save", message: "Upload a file with at least one student.", color: "red" });
      return;
    }
    setSaving(true);
    try {
      const res = await saveStudentsBatch({
        students: rows,
        programme_type: config.programmeType,
        academic_year: academicYear,
      });
      if (res.success) {
        setResult(res);
        notifications.show({ title: "Upload complete", message: res.message, color: res.data.failed_uploads ? "yellow" : "green" });
        if (res.data.successful_uploads) onSaved?.();
      } else {
        notifications.show({ title: "Error", message: res.message, color: "red" });
      }
    } catch (error) {
      notifications.show({ title: "Error", message: error.response?.data?.message || "Upload failed.", color: "red" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Stack gap="md">
      <Paper withBorder p="md" radius="md">
        <Group justify="space-between" align="center" wrap="wrap" gap="sm">
          <Group gap="sm" wrap="nowrap">
            <ThemeIcon size={40} radius="md" variant="light" color="teal">
              <FaFileExcel size={17} />
            </ThemeIcon>
            <div>
              <Text fw={600} size="sm">Step 1 · Template</Text>
              <Text size="xs" c="dimmed">Download the template, fill in student details, then upload the file below.</Text>
            </div>
          </Group>
          <Button variant="light" leftSection={<FaDownload size={12} />} onClick={() => downloadTemplate(config.label)}>
            Download Template
          </Button>
        </Group>
      </Paper>
      <FileInput
        label="Upload filled Excel"
        placeholder="Select .xlsx file"
        accept=".xlsx,.xls"
        leftSection={<FaUpload size={12} />}
        size="md"
        onChange={handleFile}
      />

      {rows.length > 0 && (
        <>
          <Text size="sm" c="dimmed">{rows.length} student(s) ready to upload</Text>
          <Table.ScrollContainer minWidth={600}>
            <Table striped withTableBorder verticalSpacing="xs">
              <Table.Thead>
                <Table.Tr>{PREVIEW_KEYS.map((k) => <Table.Th key={k}>{k}</Table.Th>)}</Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rows.slice(0, 8).map((row, idx) => (
                  <Table.Tr key={idx}>
                    {PREVIEW_KEYS.map((k) => <Table.Td key={k}>{row[k] || "-"}</Table.Td>)}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {rows.length > 8 && <Text size="xs" c="dimmed">Showing first 8 of {rows.length}.</Text>}
        </>
      )}

      {result && (
        <Alert color={result.data.failed_uploads ? "yellow" : "green"} title="Result">
          <Text size="sm">
            {result.data.successful_uploads} saved · {result.data.skipped_invalid} invalid · {result.data.failed_uploads} failed
          </Text>
          {result.errors?.length > 0 && (
            <List size="xs" mt="xs">
              {result.errors.slice(0, 8).map((err, idx) => (
                <List.Item key={idx}>{typeof err === "string" ? err : err.error}</List.Item>
              ))}
            </List>
          )}
        </Alert>
      )}

      <Group justify="flex-end">
        <Button variant="default" onClick={onCancel}>Close</Button>
        <Button onClick={handleSave} loading={saving} disabled={!rows.length}>Upload {rows.length || ""} Students</Button>
      </Group>
    </Stack>
  );
};

export default ExcelUploadFlow;
