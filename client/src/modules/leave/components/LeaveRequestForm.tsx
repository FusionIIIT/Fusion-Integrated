import { Button, Paper, Select, Stack, TextInput, Title } from "@mantine/core";
import { useEffect, useState } from "react";
import { http } from "../../../lib/http";

interface LeaveType {
  id: number;
  name: string;
  description: string;
}

interface LeaveRequestFormProps {
  onSuccess?: () => void;
}

export default function LeaveRequestForm({ onSuccess }: LeaveRequestFormProps) {
  const [leaveTypes, setLeaveTypes] = useState<LeaveType[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    http
      .get<any>("/leave/types/")
      .then((res) => {
        const raw: any = res.data; const data = Array.isArray(raw) ? raw : (raw?.results ?? []);
        setLeaveTypes(data);
        const first = data[0];
        if (first && !selectedType) {
          setSelectedType(String(first.id));
        }
      })
      .catch((err) => {
        console.error("Failed to load leave types", err);
      });
  }, [selectedType]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedType || !startDate || !endDate) {
      setError("Please fill in all required fields.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await http.post("/leave/applications/", {
        leave_type: Number(selectedType),
        start_date: startDate,
        end_date: endDate,
        status: "pending",
      });
      setStartDate("");
      setEndDate("");
      if (onSuccess) onSuccess();
    } catch (err: unknown) {
      setError("Failed to submit leave application.");
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Paper withBorder p="md" radius="sm">
      <Title order={4} mb="sm">
        Apply for Leave
      </Title>
      {error && (
        <div style={{ color: "red", marginBottom: "0.5rem", fontSize: "0.9rem" }}>
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          <Select
            label="Leave Type"
            placeholder="Select leave type"
            data={leaveTypes.map((t) => ({ value: String(t.id), label: t.name }))}
            value={selectedType}
            onChange={setSelectedType}
            required
          />
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
          <Button type="submit" loading={submitting}>
            Submit Application
          </Button>
        </Stack>
      </form>
    </Paper>
  );
}

