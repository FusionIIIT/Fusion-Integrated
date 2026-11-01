import { useState, useEffect } from "react";
import {
  Button, Card, Container, Group, Modal, Stack, Text, TextInput, Textarea
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { ProgressReport } from "../api/types";

export default function ProgressReportsPage() {
  const [items, setItems] = useState<ProgressReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [projectId, setProjectId] = useState("");
  const [period, setPeriod] = useState("");
  const [summary, setSummary] = useState("");
  const [milestones, setMilestones] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/rspc/progress-reports", { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setItems(data.results ?? data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async () => {
    try {
      const res = await fetch("/api/v1/rspc/progress-reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          project_id: parseInt(projectId),
          reporting_period: period,
          summary,
          milestones_achieved: milestones,
        }),
      });
      if (res.ok) {
        setOpened(false);
        setProjectId("");
        setPeriod("");
        setSummary("");
        setMilestones("");
        fetchData();
      }
    } catch {
      // ignore
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Periodic Progress Reports"
        subtitle="Submit and review quarterly/annual project progress reports"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => setOpened(true)}>
            Submit Progress Report
          </Button>
        }
      />

      <Card padding="lg" mt="md">
        <DataTable<ProgressReport>
          rows={items}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No progress reports found", description: "Submit a periodic progress report to get started" }}
          columns={[
            {
              key: "reporting_period",
              header: "Reporting Period",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={500}>{r.reporting_period}</Text>
                  <Text size="xs" c="dimmed">Project ID: #{r.project}</Text>
                </Stack>
              ),
            },
            {
              key: "summary",
              header: "Executive Summary",
              render: (r) => r.summary,
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Submitted On",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Submit Progress Report" size="md">
        <Stack gap="sm">
          <TextInput
            label="Project ID"
            type="number"
            required
            placeholder="e.g. 1"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
          />
          <TextInput
            label="Reporting Period"
            required
            placeholder="e.g. Q1 2026-27 or Annual 2025-26"
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
          />
          <Textarea
            label="Executive Summary"
            required
            placeholder="Summary of research work conducted..."
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
          />
          <Textarea
            label="Milestones Achieved"
            placeholder="Specific deliverables and publications..."
            value={milestones}
            onChange={(e) => setMilestones(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Submit Report</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
