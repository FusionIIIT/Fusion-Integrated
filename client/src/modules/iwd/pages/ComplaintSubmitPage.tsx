import { useState } from "react";
import { Button, Card, Container, Select, Stack, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { http, errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function ComplaintSubmitPage() {
  const navigate = useNavigate();
  const [category, setCategory] = useState<string | null>("Civil");
  const [urgency, setUrgency] = useState<string | null>("Low");
  const [location, setLocation] = useState("");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!location.trim()) {
      notifications.show({
        color: "red",
        title: "Validation Error",
        message: "Location is required.",
      });
      return;
    }

    setSubmitting(true);
    try {
      const res = await http.post("/iwd/complaints/", {
        category,
        urgency,
        location,
        remarks,
      });
      notifications.show({
        color: "teal",
        title: "Complaint Lodged",
        message: `Complaint #${res.data.id} has been registered and auto-assigned.`,
      });
      navigate(`/iwd/complaints/${res.data.id}`);
    } catch (err) {
      notifications.show({
        color: "red",
        title: "Submission Failed",
        message: errorMessage(err),
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container size="md">
      <PageHeader
        title="Submit Maintenance Complaint"
        subtitle="Report infrastructure or electrical maintenance issues"
      />

      <Card withBorder padding="xl" radius="md" mt="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Select
              label="Maintenance Category"
              required
              data={["Civil", "Electrical"]}
              value={category}
              onChange={setCategory}
            />

            <Select
              label="Urgency Level"
              required
              data={["Low", "Medium", "High", "Urgent"]}
              value={urgency}
              onChange={setUrgency}
            />

            <TextInput
              label="Specific Location"
              placeholder="e.g. Hall 4, Room 204 or Core Lab II"
              required
              value={location}
              onChange={(e) => setLocation(e.currentTarget.value)}
            />

            <Textarea
              label="Problem Description & Remarks"
              placeholder="Describe the maintenance requirement in detail..."
              minRows={3}
              value={remarks}
              onChange={(e) => setRemarks(e.currentTarget.value)}
            />

            <Button type="submit" loading={submitting} mt="md">
              Submit Complaint
            </Button>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
