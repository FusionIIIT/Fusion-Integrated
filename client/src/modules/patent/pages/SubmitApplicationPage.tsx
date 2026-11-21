import { useState, useEffect } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Input, NumberInput,
  Select, Text, TextInput, Stack, Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaTrash } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { createPatentApplication } from "../../../api";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";

interface Inventor {
  name: string;
  email: string;
  contribution_percent: number;
}

export default function SubmitApplicationPage() {
  const [formData, setFormData] = useState({
    title: "",
    abstract: "",
    description: "",
    claims: "",
    technical_domain: "",
    inventors: [{ name: "", email: "", contribution_percent: 0 }],
    filing_date: new Date().toISOString().split("T")[0],
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Set today's date as default for filing date
    setFormData(prev => ({
      ...prev,
      filing_date: new Date().toISOString().split("T")[0],
    }));
  }, []);

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const addInventor = () => {
    setFormData(prev => ({
      ...prev,
      inventors: [...prev.inventors, { name: "", email: "", contribution_percent: 0 }],
    }));
  };

  const removeInventor = (index: number) => {
    setFormData(prev => ({
      ...prev,
      inventors: prev.inventors.filter((_, i) => i !== index),
    }));
  };

  const updateInventor = (index: number, field: keyof Inventor, value: any) => {
    setFormData(prev => ({
      ...prev,
      inventors: prev.inventors.map((inv: Inventor, i) =>
        i === index ? { ...inv, [field]: value } : inv
      ),
    }));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      // Basic validation
      if (!formData.title.trim()) {
        setError("Title is required.");
        return;
      }
      if (!formData.abstract.trim()) {
        setError("Abstract is required.");
        return;
      }
      if (formData.inventors.length === 0) {
        setError("At least one inventor is required.");
        return;
      }
      for (const inv of formData.inventors) {
        if (!inv.name.trim()) {
          setError("All inventors must have a name.");
          return;
        }
        if (!inv.email.trim()) {
          setError("All inventors must have an email.");
          return;
        }
        if (inv.contribution_percent < 0 || inv.contribution_percent > 100) {
          setError(`Contribution percentage for ${inv.name} must be between 0 and 100.`);
          return;
        }
      }

      const data = {
        title: formData.title,
        abstract: formData.abstract,
        inventor_names: formData.inventors.map(inv => inv.name),
        filing_date: formData.filing_date,
      };

      await createPatentApplication(data);
      notifications.show({
        message: "Application submitted successfully!",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred while submitting the application.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Submit Patent Application"
        subtitle="Fill in the details to submit a new patent application."
      />
      <Card padding="lg">
        <Stack gap="md">
          <Title order={2}>Application Details</Title>
          
          <TextInput
            label="Title"
            value={formData.title}
            onChange={(e) => handleInputChange("title", e.target.value)}
            placeholder="Enter the title of your invention"
            required
          />

          <TextInput
            label="Abstract"
            value={formData.abstract}
            onChange={(e) => handleInputChange("abstract", e.target.value)}
            placeholder="Provide a brief summary of your invention"
            required
          />

          <TextInput
            label="Description"
            value={formData.description}
            onChange={(e) => handleInputChange("description", e.target.value)}
            placeholder="Describe your invention in detail"
          />

          <TextInput
            label="Claims"
            value={formData.claims}
            onChange={(e) => handleInputChange("claims", e.target.value)}
            placeholder="List the claims of your invention"
          />

          <TextInput
            label="Technical Domain"
            value={formData.technical_domain}
            onChange={(e) => handleInputChange("technical_domain", e.target.value)}
            placeholder="Specify the technical domain of your invention"
          />

          <Title order={3}>Inventors</Title>
          
          {formData.inventors.map((inv, index) => (
            <Card key={index} padding="sm" radius="md">
              <Stack gap="xs">
                <TextInput
                  label={`Name ${index + 1}`}
                  value={inv.name}
                  onChange={(e) => updateInventor(index, "name", e.target.value)}
                  placeholder="Enter inventor's name"
                />

                <TextInput
                  label={`Email ${index + 1}`}
                  type="email"
                  value={inv.email}
                  onChange={(e) => updateInventor(index, "email", e.target.value)}
                  placeholder="Enter inventor's email"
                />

                <NumberInput
                  label={`Contribution Percentage ${index + 1}`}
                  value={inv.contribution_percent}
                  onChange={(value) => updateInventor(index, "contribution_percent", Number(value))}
                  min={0}
                  max={100}
                  step={1}
                />

                {formData.inventors.length > 1 && (
                  <ActionIcon
                    variant="subtle"
                    color="red"
                    onClick={() => removeInventor(index)}
                  >
                    <FaTrash size={14} />
                  </ActionIcon>
                )}
              </Stack>
            </Card>
          ))}

          <Button
            variant="outline"
            leftSection={<FaPlus />}
            onClick={addInventor}
          >
            Add Inventor
          </Button>

          <Title order={3}>Filing Date</Title>

          <TextInput
            label="Filing Date"
            type="date"
            value={formData.filing_date}
            onChange={(e) => handleInputChange("filing_date", e.target.value)}
          />

          <Button
            type="button"
            onClick={handleSubmit}
            loading={isSubmitting}
            fullWidth
            color="blue"
          >
            Submit Application
          </Button>
        </Stack>
      </Card>
    </Container>
  );
}
