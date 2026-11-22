import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { FaFileAlt } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useCreateApplication } from "../api/hooks";

export default function NewApplicationPage() {
  const navigate = useNavigate();
  const createMutation = useCreateApplication();

  const [title, setTitle] = useState("");
  const [fieldOfInvention, setFieldOfInvention] = useState("");
  const [filingType, setFilingType] = useState<string | null>("provisional");
  const [abstract, setAbstract] = useState("");
  const [claims, setClaims] = useState("");
  const [detailedDescription, setDetailedDescription] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      notifications.show({ title: "Validation Error", message: "Title is required.", color: "red" });
      return;
    }

    createMutation.mutate(
      {
        title,
        field_of_invention: fieldOfInvention,
        filing_type: filingType || "provisional",
        abstract,
        claims,
        detailed_description: detailedDescription,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            title: "Success",
            message: `Patent draft created: ${data.application_no}`,
            color: "green",
          });
          navigate(`/pms/applications/${data.id}`);
        },
        onError: (err: any) => {
          notifications.show({
            title: "Creation Failed",
            message: err.response?.data?.error || "Failed to create application draft.",
            color: "red",
          });
        },
      }
    );
  };

  return (
    <Container size="md" py="md">
      <PageHeader
        title="New Patent Draft"
        subtitle="Initiate an invention disclosure and prepare provisional or complete specification."
        icon={<FaFileAlt size={26} />}
      />

      <Card shadow="xs" padding="lg" radius="md" withBorder mt="md">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <TextInput
              label="Invention Title"
              placeholder="e.g. High-Pressure Alkaline Water Electrolyzer"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />

            <Group grow>
              <TextInput
                label="Field of Invention"
                placeholder="e.g. Clean Energy / Materials"
                value={fieldOfInvention}
                onChange={(e) => setFieldOfInvention(e.target.value)}
              />
              <Select
                label="Filing Type"
                data={[
                  { value: "provisional", label: "Provisional Specification" },
                  { value: "complete", label: "Complete Specification" },
                  { value: "pct", label: "PCT International Application" },
                ]}
                value={filingType}
                onChange={setFilingType}
                required
              />
            </Group>

            <Textarea
              label="Technical Abstract"
              placeholder="Summary of the technical novelty and industrial utility..."
              minRows={3}
              required
              value={abstract}
              onChange={(e) => setAbstract(e.target.value)}
            />

            <Textarea
              label="Detailed Technical Description"
              placeholder="Detailed description of components, embodiments, and working examples..."
              minRows={5}
              value={detailedDescription}
              onChange={(e) => setDetailedDescription(e.target.value)}
            />

            <Textarea
              label="Patent Claims"
              placeholder="1. An electrolyzer stack comprising..."
              minRows={4}
              required
              value={claims}
              onChange={(e) => setClaims(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => navigate("/pms")}>
                Cancel
              </Button>
              <Button type="submit" loading={createMutation.isPending} color="blue">
                Save Application Draft
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
