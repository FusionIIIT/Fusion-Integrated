import { useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Loader, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import { mmsApi } from "../api";
import type { RebateRequest } from "../types";

export default function RebatesPage() {
  const [rebates, setRebates] = useState<RebateRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function fetchRebates() {
    setLoading(true);
    try {
      const data = await mmsApi.getMyRebates();
      setRebates(data);
    } catch (err) {
      console.error("Failed to fetch rebates", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRebates();
  }, []);

  async function handleApply(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const newRebate = await mmsApi.applyRebate({
        start_date: startDate,
        end_date: endDate,
        reason,
      });
      setRebates([newRebate, ...rebates]);
      setSuccess("Rebate request submitted successfully!");
      setStartDate("");
      setEndDate("");
      setReason("");
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Failed to apply for rebate.";
      setError(msg || "Failed to apply for rebate.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Container size="lg" py="md">
      <Stack gap="md">
        <div>
          <Title order={2}>Mess Rebates</Title>
          <Text c="dimmed">Apply for meal rebates (minimum 3 consecutive days, at least 1 day advance notice).</Text>
        </div>

        {error && <Alert color="red">{error}</Alert>}
        {success && <Alert color="green">{success}</Alert>}

        <Card withBorder padding="md" radius="md">
          <Title order={4} mb="xs">Apply for Mess Rebate</Title>
          <form onSubmit={handleApply}>
            <Group grow mb="xs">
              <TextInput
                label="Start Date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                required
              />
              <TextInput
                label="End Date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                required
              />
            </Group>
            <TextInput
              label="Reason for Absence"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Home Visit / Academic Conference"
              required
              mb="sm"
            />
            <Button type="submit" color="blue" loading={submitting}>
              Submit Rebate
            </Button>
          </form>
        </Card>

        <Card withBorder radius="md">
          <Title order={4} p="md" pb="xs">My Rebate History</Title>
          {loading ? (
            <Group justify="center" py="xl"><Loader /></Group>
          ) : rebates.length === 0 ? (
            <Text c="dimmed" p="md">No rebate requests submitted yet.</Text>
          ) : (
            <Table striped highlightOnHover>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>ID</Table.Th>
                  <Table.Th>Dates</Table.Th>
                  <Table.Th>Duration</Table.Th>
                  <Table.Th>Reason</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rebates.map((r) => (
                  <Table.Tr key={r.id}>
                    <Table.Td>#{r.id}</Table.Td>
                    <Table.Td>{r.start_date} to {r.end_date}</Table.Td>
                    <Table.Td>{r.duration_days} days</Table.Td>
                    <Table.Td>{r.reason}</Table.Td>
                    <Table.Td>
                      <Badge color={r.status === "APPROVED" ? "green" : r.status === "PENDING" ? "yellow" : "red"}>
                        {r.status}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Card>
      </Stack>
    </Container>
  );
}

