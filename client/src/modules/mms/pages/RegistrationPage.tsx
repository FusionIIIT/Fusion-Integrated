import { useEffect, useState } from "react";
import { Alert, Badge, Button, Card, Container, Group, Loader, Stack, Text, TextInput, Title } from "@mantine/core";
import { mmsApi } from "../api";
import type { MessRegistration, RegistrationWindow } from "../types";

export default function RegistrationPage() {
  const [registration, setRegistration] = useState<MessRegistration | null>(null);
  const [window, setWindow] = useState<RegistrationWindow | null>(null);
  const [loading, setLoading] = useState(true);
  const [startDate, setStartDate] = useState("");
  const [remarks, setRemarks] = useState("");
  const [deregReason, setDeregReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function loadData() {
    setLoading(true);
    try {
      try {
        const reg = await mmsApi.getMyRegistration();
        setRegistration(reg);
      } catch {
        setRegistration(null);
      }
      try {
        const win = await mmsApi.getCurrentWindow();
        setWindow(win);
      } catch {
        setWindow(null);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const reg = await mmsApi.submitRegistration({
        start_date: startDate,
        remarks,
      });
      setRegistration(reg);
      setSuccess("Mess registration submitted successfully!");
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Failed to submit registration.";
      setError(msg || "Failed to submit registration.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeregister(e: React.FormEvent) {
    e.preventDefault();
    if (!registration) return;
    setError(null);
    setSuccess(null);
    setSubmitting(true);
    try {
      const updated = await mmsApi.submitDeregistration(registration.id, deregReason);
      setRegistration(updated);
      setSuccess("Deregistration request submitted to Mess Caretaker.");
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : "Failed to submit deregistration.";
      setError(msg || "Failed to submit deregistration.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <Container size="md" py="xl"><Group justify="center"><Loader /></Group></Container>;
  }

  return (
    <Container size="md" py="md">
      <Stack gap="md">
        <div>
          <Title order={2}>Mess Registration & Allocation</Title>
          <Text c="dimmed">Manage student mess registration, status, and deregistration requests.</Text>
        </div>

        {error && <Alert color="red">{error}</Alert>}
        {success && <Alert color="green">{success}</Alert>}

        {registration ? (
          <Card withBorder padding="md" radius="md">
            <Title order={4} mb="xs">My Current Registration</Title>
            <Stack gap="xs">
              <Group justify="space-between">
                <Text fw={500}>Status:</Text>
                <Badge color={registration.status === "REGISTERED" ? "green" : registration.status === "PENDING" ? "yellow" : "red"}>
                  {registration.status}
                </Badge>
              </Group>
              <Text size="sm">Mess: {registration.mess_name}</Text>
              <Text size="sm">Start Date: {registration.start_date}</Text>
              {registration.end_date && <Text size="sm">End Date: {registration.end_date}</Text>}
              {registration.remarks && <Text size="sm" c="dimmed">Remarks: {registration.remarks}</Text>}

              {registration.status === "REGISTERED" && (
                <form onSubmit={handleDeregister}>
                  <Stack gap="xs" mt="md">
                    <Title order={5}>Request Deregistration</Title>
                    <TextInput
                      label="Reason for Deregistration"
                      value={deregReason}
                      onChange={(e) => setDeregReason(e.target.value)}
                      placeholder="e.g. Vacation / Semester Leave"
                      required
                    />
                    <Button type="submit" color="red" variant="light" loading={submitting}>
                      Submit Deregistration
                    </Button>
                  </Stack>
                </form>
              )}
            </Stack>
          </Card>
        ) : (
          <Card withBorder padding="md" radius="md">
            <Title order={4} mb="xs">Apply for Mess Registration</Title>
            {window && window.is_open ? (
              <form onSubmit={handleRegister}>
                <Stack gap="xs">
                  <Text size="sm" c="dimmed">Registration Window: {window.name} ({window.start_date} to {window.end_date})</Text>
                  <TextInput
                    label="Desired Start Date"
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    required
                  />
                  <TextInput
                    label="Remarks (optional)"
                    value={remarks}
                    onChange={(e) => setRemarks(e.target.value)}
                    placeholder="Dietary preferences or student notes"
                  />
                  <Button type="submit" color="blue" loading={submitting}>
                    Submit Application
                  </Button>
                </Stack>
              </form>
            ) : (
              <Text c="dimmed" size="sm">No mess registration window is currently open.</Text>
            )}
          </Card>
        )}
      </Stack>
    </Container>
  );
}
