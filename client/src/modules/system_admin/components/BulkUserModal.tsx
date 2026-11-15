import { useState } from "react";
import {
  Alert,
  Anchor,
  Box,
  Button,
  FileInput,
  Group,
  List,
  Progress,
  Stack,
  Text,
  ThemeIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheckCircle, FaExclamationTriangle, FaFileCsv, FaUpload } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { useBulkUploadUsers } from "../api/hooks";

export function BulkUserModal({
  opened,
  onClose,
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const bulkUpload = useBulkUploadUsers();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<{
    total: number;
    processed: number;
    failed: number;
    error_details: unknown[];
  } | null>(null);

  const handleDownloadSample = () => {
    const csvContent =
      "user_kind,name,institute_email,institute_id,department,programme,discipline,batch_year,employee_id\n" +
      "student,Aarav Patel,aarav.p@iiitdmj.ac.in,24BCS001,CSE,B.Tech,CSE,2024,\n" +
      "student,Ananya Singh,ananya.s@iiitdmj.ac.in,24ECE012,ECE,B.Tech,ECE,2024,\n" +
      "faculty,Dr. Vikram Rao,vikram.rao@iiitdmj.ac.in,FAC098,ME,,Mechanical,,EMP-FAC-098\n" +
      "staff,Ramesh Kumar,ramesh.k@iiitdmj.ac.in,STF042,Admin,,,STF-2024-042";

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "bulk_users_sample.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleSubmit = () => {
    if (!file) {
      notifications.show({
        color: "red",
        title: "No File Selected",
        message: "Please choose a CSV file with user records.",
      });
      return;
    }

    const formData = new FormData();
    formData.append("csv_file", file);

    bulkUpload.mutate(formData, {
      onSuccess: (res) => {
        setResult(res);
        notifications.show({
          color: res.failed > 0 ? "yellow" : "green",
          title: "Bulk Onboarding Processed",
          message: `Processed: ${res.processed} successful, ${res.failed} errors.`,
        });
      },
      onError: (err) => {
        notifications.show({
          color: "red",
          title: "Upload Failed",
          message: errorMessage(err),
        });
      },
    });
  };

  const handleClose = () => {
    setFile(null);
    setResult(null);
    onClose();
  };

  return (
    <FormModal
      opened={opened}
      onClose={handleClose}
      title="Bulk User Onboarding"
      subtitle="Import up to 1,000 student, faculty, or staff records using CSV"
      onSubmit={handleSubmit}
      submitting={bulkUpload.isPending}
      submitLabel="Upload & Process"
      size="lg"
    >
      <Stack gap="md">
        <Alert
          icon={<FaFileCsv size={16} />}
          title="CSV Format Requirements"
          color="blue"
        >
          <Text size="sm">
            CSV must include headers: <code>user_kind</code>, <code>name</code>,{" "}
            <code>institute_email</code>, <code>institute_id</code>.
          </Text>
          <Group mt="xs">
            <Anchor component="button" size="xs" onClick={handleDownloadSample}>
              Download Sample CSV Template
            </Anchor>
          </Group>
        </Alert>

        <FileInput
          label="Select CSV Spreadsheet"
          placeholder="Choose .csv file"
          leftSection={<FaUpload size={14} />}
          accept=".csv,text/csv"
          value={file}
          onChange={setFile}
          required
        />

        {result && (
          <Box p="md" style={{ border: "1px solid #e0e0e0", borderRadius: 8 }}>
            <Group justify="space-between" mb="xs">
              <Text fw={600} size="sm">Processing Summary</Text>
              <Text size="xs" c="dimmed">Total Rows: {result.total}</Text>
            </Group>

            <Progress.Root size="xl" mb="md">
              <Progress.Section
                value={result.total ? (result.processed / result.total) * 100 : 0}
                color="green"
              >
                <Progress.Label>{result.processed} Created</Progress.Label>
              </Progress.Section>
              <Progress.Section
                value={result.total ? (result.failed / result.total) * 100 : 0}
                color="red"
              >
                <Progress.Label>{result.failed} Failed</Progress.Label>
              </Progress.Section>
            </Progress.Root>

            {result.failed > 0 && (
              <Stack gap="xs">
                <Group gap="xs">
                  <ThemeIcon color="red" size="sm" variant="light">
                    <FaExclamationTriangle size={12} />
                  </ThemeIcon>
                  <Text size="xs" fw={600} c="red">
                    Validation Errors Encountered:
                  </Text>
                </Group>
                <List size="xs" c="dimmed" spacing="xs">
                  {result.error_details.slice(0, 5).map((err: any, idx) => (
                    <List.Item key={idx}>
                      Line {err.line} ({err.institute_id || "Unknown"}):{" "}
                      {typeof err.errors === "object"
                        ? JSON.stringify(err.errors)
                        : String(err.errors)}
                    </List.Item>
                  ))}
                  {result.error_details.length > 5 && (
                    <Text size="xs" c="dimmed" fs="italic">
                      ...and {result.error_details.length - 5} more errors
                    </Text>
                  )}
                </List>
              </Stack>
            )}
          </Box>
        )}
      </Stack>
    </FormModal>
  );
}
