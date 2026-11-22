import { useState } from "react";
import { Button, Card, Container, Group, Select, Stack, TextInput, Textarea } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateApplication } from "../api/hooks";

export default function NewApplicationPage() {
  const navigate = useNavigate();
  const createMutation = useCreateApplication();

  const [title, setTitle] = useState("");
  const [abstract, setAbstract] = useState("");
  const [description, setDescription] = useState("");
  const [claims, setClaims] = useState("");
  const [domainCategory, setDomainCategory] = useState("Computer Science");
  const [jurisdiction, setJurisdiction] = useState("IN");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !abstract.trim() || !description.trim() || !claims.trim()) {
      notifications.show({
        color: "red",
        title: "Required fields missing",
        message: "Title, abstract, description, and claims are required per BR-PMS-017.",
      });
      return;
    }

    createMutation.mutate(
      {
        title: title.trim(),
        abstract: abstract.trim(),
        description: description.trim(),
        claims: claims.trim(),
        domain_category: domainCategory,
        jurisdiction,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            color: "green",
            title: "Application submitted",
            message: `Patent application "${data.title}" was submitted successfully.`,
          });
          navigate("/patents/mine");
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Submission failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <Container size="md">
      <PageHeader
        title="New Patent Application"
        subtitle="Submit a technical invention disclosure for institutional patent evaluation"
      />

      <Card padding="lg" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="Invention Title"
              placeholder="e.g., Adaptive Autonomous Drone Navigation System"
              required
              value={title}
              onChange={(e) => setTitle(e.currentTarget.value)}
            />

            <Select
              label="Domain Category"
              data={[
                "Computer Science",
                "Electrical & Electronics",
                "Mechanical Engineering",
                "Biotechnology",
                "Chemical Engineering",
                "Material Sciences",
              ]}
              required
              value={domainCategory}
              onChange={(v) => setDomainCategory(v || "Computer Science")}
            />

            <Select
              label="Jurisdiction"
              data={[
                { value: "IN", label: "India (IPO)" },
                { value: "US", label: "United States (USPTO)" },
                { value: "EP", label: "European Patent Office (EPO)" },
                { value: "WO", label: "WIPO PCT International" },
              ]}
              required
              value={jurisdiction}
              onChange={(v) => setJurisdiction(v || "IN")}
            />

            <Textarea
              label="Abstract"
              placeholder="Brief summary of the technical disclosure..."
              required
              minRows={3}
              value={abstract}
              onChange={(e) => setAbstract(e.currentTarget.value)}
            />

            <Textarea
              label="Detailed Technical Description"
              placeholder="Full technical architecture, implementation, and novelty details..."
              required
              minRows={6}
              value={description}
              onChange={(e) => setDescription(e.currentTarget.value)}
            />

            <Textarea
              label="Patent Claims"
              placeholder="1. A system comprising... \n2. The system of claim 1 further comprising..."
              required
              minRows={4}
              value={claims}
              onChange={(e) => setClaims(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/patents/mine")}>
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending}>
                Submit Application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
