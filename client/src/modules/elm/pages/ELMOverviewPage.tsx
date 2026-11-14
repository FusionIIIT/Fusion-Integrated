import { Stack, Text, Title, TextInput, Button, Group, Paper, Textarea, Select } from "@mantine/core";
import { useState } from "react";
import { http, errorMessage } from "../../../lib/http";
import { notifications } from "@mantine/notifications";
import type { FormEvent } from "react";

interface LeaveApplication {
  id: number;
  category: string;
  start_date: string;
  end_date: string;
  purpose: string;
  status: string;
  requested_days: number;
}

const categories = ["CL", "RH", "SCL", "EL", "COL", "VL"];

export default function ELMOverviewPage() {
  const [category, setCategory] = useState<string | null>(null);
  const [start_date, setStartDate] = useState<string>("");
  const [end_date, setEndDate] = useState<string>("");
  const [purpose, setPurpose] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [requests, setRequests] = useState<LeaveApplication[]>([]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!category || !start_date || !end_date || !purpose) {
      notifications.show({
        title: "Validation Error",
        message: "All fields are required.",
        color: "red",
      });
      return;
    }

    setLoading(true);
    try {
      const response = await http.post('/elm/applications', { category, start_date, end_date, purpose });
      notifications.show({
        title: "Success",
        message: "Leave request submitted successfully.",
        color: "green",
      });
      setRequests([...requests, response.data]);
      setCategory(null);
      setStartDate("");
      setEndDate("");
      setPurpose("");
    } catch (error) {
      notifications.show({
        title: "Error",
        message: errorMessage(error),
        color: "red",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Stack gap="md">
      <Title order={2}>Employee Leave Management</Title>
      <Text>
        ELM is being integrated as an independent module of Fusion ERP.
      </Text>

      <Paper shadow="sm" p="md">
        <Title order={3}>Request Leave</Title>
        <form onSubmit={handleSubmit}>
          <Select
            label="Category"
            placeholder="e.g., CL"
            data={categories}
            value={category}
            onChange={setCategory}
          />
          <TextInput
            label="Start Date"
            type="date"
            placeholder="e.g., 2023-10-01"
            value={start_date}
            onChange={(e) => setStartDate(e.target.value)}
          />
          <TextInput
            label="End Date"
            type="date"
            placeholder="e.g., 2023-10-01"
            value={end_date}
            onChange={(e) => setEndDate(e.target.value)}
          />
          <Textarea
            label="Purpose"
            placeholder="Describe your leave request"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button type="submit" loading={loading}>
              Submit Request
            </Button>
          </Group>
        </form>
      </Paper>

      <Paper shadow="sm" p="md">
        <Title order={3}>Your Leave Requests</Title>
        {requests.length > 0 ? (
          requests.map((request, index) => (
            <Text key={index}>{`${request.category} / ${request.start_date} - ${request.end_date} / ${request.status}`}</Text>
          ))
        ) : (
          <Text>No leave requests yet.</Text>
        )}
      </Paper>
    </Stack>
  );
}
