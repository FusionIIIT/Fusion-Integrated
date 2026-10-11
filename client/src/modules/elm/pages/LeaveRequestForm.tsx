import { useState } from "react";
import { Container, Card, Stack, TextInput, Select, Textarea, Button, Group } from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function LeaveRequestForm() {
  const [category, setCategory] = useState<string | null>("cl");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
  };

  return (
    <Container size="md">
      <PageHeader
        title="Apply for Leave"
        subtitle="Submit a new employee leave request"
      />
      <Card padding="lg" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack>
            <Select
              label="Leave Category"
              placeholder="Select category"
              data={[
                { value: "cl", label: "Casual Leave (CL)" },
                { value: "rh", label: "Restricted Holiday (RH)" },
                { value: "scl", label: "Special Casual Leave (SCL)" },
                { value: "el", label: "Earned Leave (EL)" },
                { value: "vl", label: "Faculty Vacation Leave (VL)" },
                { value: "col", label: "Commuted Leave (COL)" },
              ]}
              value={category}
              onChange={setCategory}
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
            <Textarea
              label="Reason"
              placeholder="Enter reason for leave"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
            />
            <Group justify="flex-end" mt="md">
              <Button variant="default" component={Link} to="/elm/leave-requests">
                Cancel
              </Button>
              <Button type="submit">Submit Request</Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
