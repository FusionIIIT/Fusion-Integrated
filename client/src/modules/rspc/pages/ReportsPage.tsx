import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaChartBar } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";

interface ReportItem {
  id: number;
  project: string;
  type: string;
  period: string;
  submitted_date: string;
  status: string;
}

const INITIAL_REPORTS: ReportItem[] = [
  {
    id: 1,
    project: "AI-Powered Renewable Energy Grid Forecasting",
    type: "Annual Progress Report",
    period: "2025-04 to 2026-03",
    submitted_date: "2026-04-10",
    status: "ACCEPTED",
  },
  {
    id: 2,
    project: "Advanced Composite Materials for Aerospace Systems",
    type: "Utilization Certificate",
    period: "FY 2025-26",
    submitted_date: "2026-05-02",
    status: "UNDER_REVIEW",
  },
];

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>(INITIAL_REPORTS);
  const [opened, { open, close }] = useDisclosure(false);

  const [project, setProject] = useState("");
  const [reportType, setReportType] = useState<string | null>("Progress Report");
  const [period, setPeriod] = useState("");
  const [summary, setSummary] = useState("");

  const handleSubmit = () => {
    if (!project || !period) {
      notifications.show({
        title: "Validation Error",
        message: "Please specify project and reporting period.",
        color: "red",
      });
      return;
    }

    const newRpt: ReportItem = {
      id: reports.length + 1,
      project,
      type: reportType || "Progress Report",
      period,
      submitted_date: new Date().toISOString().slice(0, 10),
      status: "SUBMITTED",
    };

    setReports([newRpt, ...reports]);
    notifications.show({
      title: "Report Submitted",
      message: `${reportType} for "${project}" submitted successfully.`,
      color: "green",
    });

    setProject("");
    setPeriod("");
    setSummary("");
    close();
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Progress & Closure Reports"
        subtitle="Submit periodic progress reports, utilization certificates, and project completion records"
        action={
          <Button leftSection={<FaPlus />} onClick={open}>
            Submit Report
          </Button>
        }
      />

      <Card withBorder radius="md">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Project</Table.Th>
              <Table.Th>Report Type</Table.Th>
              <Table.Th>Reporting Period</Table.Th>
              <Table.Th>Submission Date</Table.Th>
              <Table.Th>Review Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {reports.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>
                  <Text fw={600} size="sm">
                    {r.project}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="light" color="blue">
                    {r.type}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{r.period}</Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {r.submitted_date}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge
                    color={r.status === "ACCEPTED" ? "green" : "yellow"}
                    variant="filled"
                  >
                    {r.status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={opened} onClose={close} title="Submit Periodic / Closure Report">
        <Stack gap="sm">
          <TextInput
            label="Project Title"
            placeholder="Select project"
            required
            value={project}
            onChange={(e) => setProject(e.currentTarget.value)}
          />
          <Select
            label="Report Category"
            data={["Annual Progress Report", "Utilization Certificate", "Project Closure Report"]}
            value={reportType}
            onChange={setReportType}
          />
          <TextInput
            label="Period Covered"
            placeholder="e.g. 2025-26 or Final Closure"
            required
            value={period}
            onChange={(e) => setPeriod(e.currentTarget.value)}
          />
          <Textarea
            label="Executive Summary & Achievements"
            placeholder="Key highlights and deliverables achieved"
            rows={3}
            value={summary}
            onChange={(e) => setSummary(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={close}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>Submit Report</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
