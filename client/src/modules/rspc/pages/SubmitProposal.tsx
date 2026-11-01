import React, { useState } from "react";
import { Container, Card, Stack, TextInput, Textarea, NumberInput, Button, Title, Alert } from "@mantine/core";
import { http, errorMessage } from "../../../lib/http";

const SubmitProposal = () => {
  const [formData, setFormData] = useState({
    title: "",
    objectives: "",
    start_date: "",
    end_date: "",
    budget: 0,
    funding_agency: "",
    resource_requirements: "",
    department: "",
  });

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    try {
      const response = await http.post("/rspc/proposals/", formData);
      setFormData({
        title: "",
        objectives: "",
        start_date: "",
        end_date: "",
        budget: 0,
        funding_agency: "",
        resource_requirements: "",
        department: "",
      });
      setSuccess(true);
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <Container>
      <Card shadow="sm" padding="lg">
        <Title order={2}>Submit Research Proposal</Title>
        {error && <Alert color="red">{error}</Alert>}
        {success && <Alert color="green">Proposal submitted</Alert>}
        <form onSubmit={handleSubmit}>
          <Stack>
            <TextInput
              label="Title"
              name="title"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
            />
            <Textarea
              label="Objectives"
              name="objectives"
              value={formData.objectives}
              onChange={(e) => setFormData({ ...formData, objectives: e.target.value })}
              required
            />
            <TextInput
              label="Start Date"
              name="start_date"
              type="date"
              value={formData.start_date}
              onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
              required
            />
            <TextInput
              label="End Date"
              name="end_date"
              type="date"
              value={formData.end_date}
              onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
              required
            />
            <NumberInput
              label="Budget"
              name="budget"
              value={formData.budget}
              onChange={(value) => setFormData({ ...formData, budget: value })}
              required
            />
            <TextInput
              label="Funding Agency"
              name="funding_agency"
              value={formData.funding_agency}
              onChange={(e) => setFormData({ ...formData, funding_agency: e.target.value })}
              required
            />
            <Textarea
              label="Resource Requirements"
              name="resource_requirements"
              value={formData.resource_requirements}
              onChange={(e) => setFormData({ ...formData, resource_requirements: e.target.value })}
              required
            />
            <TextInput
              label="Department"
              name="department"
              value={formData.department}
              onChange={(e) => setFormData({ ...formData, department: e.target.value })}
              required
            />
            <Button type="submit">Submit Proposal</Button>
          </Stack>
        </form>
      </Card>
    </Container>
  );
};

export default SubmitProposal;
