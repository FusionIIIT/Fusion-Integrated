import { useState } from "react";
import { Alert, Button, Card, Container, Group, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { Link } from "react-router-dom";

import { errorMessage } from "../lib/http";
import { PageHeader } from "../ui/components/PageHeader";
import { useRequestCompanyRegistration } from "../modules/placement/api/hooks";

export default function CompanyRegistrationPage() {
  const request = useRequestCompanyRegistration();
  const [form, setForm] = useState({
    name: "", sector: "", website: "", hq_city: "", contact_name: "",
    contact_email: "", contact_phone: "",
  });
  const [submitted, setSubmitted] = useState(false);
  const update = (field: keyof typeof form, value: string) =>
    setForm((current) => ({ ...current, [field]: value }));

  return (
    <Container size="sm" py="xl">
      <PageHeader title="Company registration"
        subtitle="Request access to Fusion Placement Cell" />
      {submitted ? (
        <Alert color="green" title="Request submitted">
          Your request is pending the institute&apos;s external approval process.
          <Text mt="sm"><Link to="/recruiter/login">Return to recruiter login</Link></Text>
        </Alert>
      ) : (
        <Card withBorder padding="lg">
          <Stack>
            <Title order={3}>Company details</Title>
            <Text size="sm" c="dimmed">
              Submitting this form does not grant recruiter access. The institute
              records its approval decision separately.
            </Text>
            <TextInput label="Company name" required value={form.name}
              onChange={(e) => update("name", e.currentTarget.value)} />
            <Group grow>
              <TextInput label="Sector" value={form.sector}
                onChange={(e) => update("sector", e.currentTarget.value)} />
              <TextInput label="Headquarters city" value={form.hq_city}
                onChange={(e) => update("hq_city", e.currentTarget.value)} />
            </Group>
            <TextInput label="Website" placeholder="https://example.com"
              value={form.website} onChange={(e) => update("website", e.currentTarget.value)} />
            <TextInput label="Contact name" value={form.contact_name}
              onChange={(e) => update("contact_name", e.currentTarget.value)} />
            <TextInput label="Contact email" type="email" value={form.contact_email}
              onChange={(e) => update("contact_email", e.currentTarget.value)} />
            <TextInput label="Contact phone" value={form.contact_phone}
              onChange={(e) => update("contact_phone", e.currentTarget.value)} />
            {request.error && <Alert color="red">{errorMessage(request.error)}</Alert>}
            <Button loading={request.isPending} disabled={!form.name.trim()}
              onClick={() => request.mutate(form, {
                onSuccess: () => {
                  notifications.show({
                    color: "green", title: "Request submitted",
                    message: "The company remains pending institute review.",
                  });
                  setSubmitted(true);
                },
              })}>Submit registration request</Button>
            <Text size="sm" ta="center"><Link to="/recruiter/login">Recruiter login</Link></Text>
          </Stack>
        </Card>
      )}
    </Container>
  );
}
