import { useState, useEffect } from "react";
import {
  Button, Card, Container, Group, Modal, Stack, Text, TextInput, Textarea
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { ResearchProject } from "../api/types";

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<ResearchProject[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [title, setTitle] = useState("");
  const [objectives, setObjectives] = useState("");
  const [fundingSource, setFundingSource] = useState("");
  const [budget, setBudget] = useState("");

  const fetchProposals = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/rspc/proposals", { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setProposals(data.results ?? data);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProposals();
  }, []);

  const handleCreate = async () => {
    try {
      const res = await fetch("/api/v1/rspc/proposals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          title,
          objectives,
          funding_source: fundingSource,
          budget_requested: budget ? parseFloat(budget) : null,
        }),
      });
      if (res.ok) {
        setOpened(false);
        setTitle("");
        setObjectives("");
        setFundingSource("");
        setBudget("");
        fetchProposals();
      }
    } catch {
      // ignore
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Research Project Proposals"
        subtitle="Submit, review, and track research project proposals"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => setOpened(true)}>
            New Proposal
          </Button>
        }
      />

      <Card padding="lg" mt="md">
        <DataTable<ResearchProject>
          rows={proposals}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No proposals found", description: "Submit a new proposal to get started" }}
          columns={[
            {
              key: "title",
              header: "Title",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={500}>{r.title}</Text>
                  <Text size="xs" c="dimmed">ID: #{r.id} • Dept: {r.department || "General"}</Text>
                </Stack>
              ),
            },
            {
              key: "funding_source",
              header: "Funding Source",
              render: (r) => r.funding_source || "—",
            },
            {
              key: "budget",
              header: "Budget Requested",
              render: (r) => r.budget_requested ? `₹${Number(r.budget_requested).toLocaleString()}` : "—",
            },
            {
              key: "status",
              header: "Status",
              render: (r) => <StatusBadge status={r.status} />,
            },
            {
              key: "created_at",
              header: "Created",
              render: (r) => new Date(r.created_at).toLocaleDateString(),
            },
          ]}
        />
      </Card>

      <Modal opened={opened} onClose={() => setOpened(false)} title="Submit Research Proposal" size="lg">
        <Stack gap="sm">
          <TextInput
            label="Proposal Title"
            required
            placeholder="Enter proposal title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <TextInput
            label="Funding Agency / Source"
            required
            placeholder="e.g. DST, SERB, ISRO, DRDO"
            value={fundingSource}
            onChange={(e) => setFundingSource(e.target.value)}
          />
          <TextInput
            label="Estimated Budget (INR)"
            placeholder="e.g. 5000000"
            type="number"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
          />
          <Textarea
            label="Research Objectives"
            required
            placeholder="Describe objectives and scope..."
            minRows={3}
            value={objectives}
            onChange={(e) => setObjectives(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Save Draft</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
