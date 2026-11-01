import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Grid,
  Group,
  Modal,
  Paper,
  Select,
  Stack,
  Table,
  Tabs,
  Text,
  Textarea,
  ThemeIcon,
} from "@mantine/core";
import {
  FaCheckCircle,
  FaDownload,
  FaExclamationCircle,
  FaFileUpload,
  FaHistory,
  FaList,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBulkCreateUsers, useBulkStatusUpdate } from "../api/hooks";
import type { BulkOperationLog } from "../api/types";

const SAMPLE_CSV = `user_type,institute_id,email,first_name,last_name,department,programme,discipline,batch_year,employee_id
student,2024CS101,student101@iiitdmj.ac.in,Rahul,Sharma,Computer Science & Engineering,B.Tech,CSE,2024,
student,2024EC102,student102@iiitdmj.ac.in,Sneha,Patel,Electronics & Communication Engineering,B.Tech,ECE,2024,
faculty,FAC201,prof.gupta@iiitdmj.ac.in,Dr. Amit,Gupta,Computer Science & Engineering,,,,EMP301
staff,STF301,manoj.v@iiitdmj.ac.in,Manoj,Verma,Administration,,,,EMP401`;

export default function BulkUsersPage() {
  const [csvContent, setCsvContent] = useState("");
  const [statusUserIds, setStatusUserIds] = useState("");
  const [targetStatus, setTargetStatus] = useState<string>("deactivated");
  const [statusReason, setStatusReason] = useState("");
  const [lastResult, setLastResult] = useState<BulkOperationLog | null>(null);

  const bulkCreateMutation = useBulkCreateUsers();
  const bulkStatusMutation = useBulkStatusUpdate();

  const handleDownloadSample = () => {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sample_user_import.csv";
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleBulkCreate = async () => {
    if (!csvContent.trim()) return;

    // Parse simple CSV rows
    const lines = csvContent.trim().split("\n");
    if (lines.length <= 1) return;

    const headers = lines[0].split(",").map((h) => h.trim());
    const records = [];

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;
      const values = line.split(",").map((v) => v.trim());
      const rec: Record<string, unknown> = {};
      headers.forEach((h, idx) => {
        rec[h] = values[idx] || "";
      });
      if (rec.batch_year && !isNaN(Number(rec.batch_year))) {
        rec.batch_year = Number(rec.batch_year);
      }
      records.push(rec);
    }

    try {
      const res = await bulkCreateMutation.mutateAsync(records);
      setLastResult(res);
      setCsvContent("");
    } catch {
      // Error handled
    }
  };

  const handleBulkStatus = async () => {
    if (!statusUserIds.trim() || !statusReason.trim()) return;

    const ids = statusUserIds
      .split(/[\n,]/)
      .map((s) => s.trim())
      .filter((s) => s && !isNaN(Number(s)))
      .map(Number);

    if (ids.length === 0) return;

    try {
      const res = await bulkStatusMutation.mutateAsync({
        user_ids: ids,
        target_status: targetStatus,
        reason: statusReason,
      });
      setLastResult(res);
      setStatusUserIds("");
      setStatusReason("");
    } catch {
      // Error handled
    }
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="Bulk Identity Operations"
        subtitle="Batch user onboarding and fleet-wide status administration (CFR-SA-004, BR-SA-030)"
        action={
          <Button variant="outline" leftSection={<FaDownload />} onClick={handleDownloadSample}>
            Download CSV Template
          </Button>
        }
      />

      <Tabs defaultValue="create">
        <Tabs.List>
          <Tabs.Tab value="create" leftSection={<FaFileUpload size={14} />}>
            Batch User Creation
          </Tabs.Tab>
          <Tabs.Tab value="status" leftSection={<FaList size={14} />}>
            Bulk Status Transition
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="create" pt="md">
          <Grid gutter="md">
            <Grid.Col span={{ base: 12, md: 8 }}>
              <Card withBorder p="md" radius="md">
                <Text fw={600} mb="xs">
                  Upload / Paste CSV Records
                </Text>
                <Text size="sm" c="dimmed" mb="md">
                  A single batch operation is limited to 1,000 records per policy constraint (BR-SA-030).
                </Text>

                <Textarea
                  placeholder={`Paste CSV data here with headers:
user_type,institute_id,email,first_name,last_name,department,programme,discipline,batch_year,employee_id
...`}
                  minRows={10}
                  value={csvContent}
                  onChange={(e) => setCsvContent(e.currentTarget.value)}
                  style={{ fontFamily: "monospace" }}
                />

                <Group justify="space-between" mt="md">
                  <Text size="xs" c="dimmed">
                    Rows detected: {csvContent.trim() ? Math.max(0, csvContent.trim().split("\n").length - 1) : 0}
                  </Text>
                  <Button
                    onClick={handleBulkCreate}
                    loading={bulkCreateMutation.isPending}
                    disabled={!csvContent.trim()}
                    leftSection={<FaFileUpload />}
                  >
                    Execute Batch Import
                  </Button>
                </Group>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, md: 4 }}>
              <Paper withBorder p="md" radius="md">
                <Text fw={600} mb="xs">
                  Validation Guidelines
                </Text>
                <Stack gap="xs">
                  <Text size="xs" c="dimmed">
                    • <strong>institute_id</strong>: Must be unique across all active & archived records (BR-SA-001).
                  </Text>
                  <Text size="xs" c="dimmed">
                    • <strong>email</strong>: Must belong to institutional domain @iiitdmj.ac.in (BR-SA-002).
                  </Text>
                  <Text size="xs" c="dimmed">
                    • <strong>user_type</strong>: Must be student, faculty, or staff.
                  </Text>
                  <Text size="xs" c="dimmed">
                    • <strong>Atomicity</strong>: Erroneous records are flagged with specific failure reasons while valid rows succeed.
                  </Text>
                </Stack>
              </Paper>
            </Grid.Col>
          </Grid>
        </Tabs.Panel>

        <Tabs.Panel value="status" pt="md">
          <Card withBorder p="md" radius="md" maw={800}>
            <Text fw={600} mb="xs">
              Batch Status Transition
            </Text>
            <Text size="sm" c="dimmed" mb="md">
              Update activation status across multiple basic users simultaneously.
            </Text>

            <Stack gap="sm">
              <Select
                label="Target Status"
                required
                data={[
                  { value: "deactivated", label: "Deactivate Accounts" },
                  { value: "active", label: "Reactivate Accounts" },
                ]}
                value={targetStatus}
                onChange={(v) => setTargetStatus(v || "deactivated")}
              />

              <Textarea
                label="User IDs"
                description="Enter internal User IDs separated by commas or newlines"
                placeholder="1001, 1002, 1003..."
                minRows={5}
                required
                value={statusUserIds}
                onChange={(e) => setStatusUserIds(e.currentTarget.value)}
              />

              <Textarea
                label="Administrative Justification"
                description="Mandatory rationale for batch status transition (BR-SA-025)"
                placeholder="e.g. End of semester batch graduation, or administrative suspension..."
                required
                value={statusReason}
                onChange={(e) => setStatusReason(e.currentTarget.value)}
              />

              <Group justify="flex-end" mt="md">
                <Button
                  color={targetStatus === "deactivated" ? "orange" : "green"}
                  onClick={handleBulkStatus}
                  loading={bulkStatusMutation.isPending}
                  disabled={!statusUserIds.trim() || !statusReason.trim()}
                >
                  Execute Fleet Update
                </Button>
              </Group>
            </Stack>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Result Card */}
      {lastResult && (
        <Card withBorder p="md" radius="md" mt="lg">
          <Group justify="space-between" mb="xs">
            <Text fw={600}>
              Execution Summary: Batch #{lastResult.batch_id}
            </Text>
            <Badge color={lastResult.failed_records > 0 ? "yellow" : "green"}>
              {lastResult.successful_records} Succeeded / {lastResult.total_records} Total
            </Badge>
          </Group>

          <Text size="sm" c="dimmed" mb="md">
            Operation: {lastResult.operation_type} · Failed: {lastResult.failed_records}
          </Text>

          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Record / Line</Table.Th>
                <Table.Th>Institute / User ID</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Notes</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {lastResult.detailed_log.slice(0, 50).map((entry, idx) => (
                <Table.Tr key={idx}>
                  <Table.Td>{entry.line ?? `Record ${idx + 1}`}</Table.Td>
                  <Table.Td>{entry.institute_id ?? entry.user_id ?? "—"}</Table.Td>
                  <Table.Td>
                    <Badge color={entry.status === "created" || entry.status === "updated" ? "green" : "red"}>
                      {entry.status}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c={entry.reason ? "red" : "dimmed"}>
                      {entry.reason || "Processed successfully"}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
}
