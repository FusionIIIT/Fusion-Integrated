import { useState, useEffect } from "react";
import {
  Button, Card, Container, Group, Modal, Select, Stack, Text, TextInput, Textarea
} from "@mantine/core";
import { FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import type { FinanceRequest } from "../api/types";

export default function FinancePage() {
  const [items, setItems] = useState<FinanceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [opened, setOpened] = useState(false);
  const [category, setCategory] = useState<string | null>("expenditure");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [purpose, setPurpose] = useState("");

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/rspc/finance", { credentials: "include" });
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
      const res = await fetch("/api/v1/rspc/finance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          category: category ?? "expenditure",
          description,
          amount: parseFloat(amount),
          purpose,
        }),
      });
      if (res.ok) {
        setOpened(false);
        setDescription("");
        setAmount("");
        setPurpose("");
        fetchData();
      }
    } catch {
      // ignore
    }
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Financial & Fund Requests"
        subtitle="Manage fund utilizations, expenditures, and advance sanctions"
        action={
          <Button leftSection={<FaPlus size={12} />} onClick={() => setOpened(true)}>
            New Financial Request
          </Button>
        }
      />

      <Card padding="lg" mt="md">
        <DataTable<FinanceRequest>
          rows={items}
          loading={loading}
          rowKey={(r) => r.id}
          empty={{ title: "No financial requests found", description: "Submit a financial request to get started" }}
          columns={[
            {
              key: "description",
              header: "Description",
              render: (r) => (
                <Stack gap={2}>
                  <Text fw={500}>{r.description}</Text>
                  <Text size="xs" c="dimmed">Category: {r.category} • Req #{r.id}</Text>
                </Stack>
              ),
            },
            {
              key: "amount",
              header: "Amount",
              render: (r) => `₹${Number(r.amount).toLocaleString()}`,
            },
            {
              key: "purpose",
              header: "Purpose",
              render: (r) => r.purpose || "—",
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

      <Modal opened={opened} onClose={() => setOpened(false)} title="Submit Financial Request" size="md">
        <Stack gap="sm">
          <Select
            label="Category"
            data={[
              { value: "expenditure", label: "Expenditure" },
              { value: "fund_utilisation", label: "Fund Utilisation" },
              { value: "advance", label: "Advance" },
            ]}
            value={category}
            onChange={setCategory}
          />
          <TextInput
            label="Amount (INR)"
            type="number"
            required
            placeholder="e.g. 50000"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <TextInput
            label="Purpose / Budget Head"
            placeholder="e.g. Travel, Consumables, Honorarium"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
          />
          <Textarea
            label="Detailed Description"
            required
            placeholder="Itemization and details..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setOpened(false)}>Cancel</Button>
            <Button onClick={handleCreate}>Submit Request</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
