import { useMemo, useState } from "react";
import {
  Alert, Button, Card, Container, Group, NumberInput, Stack, Text, TextInput, Textarea,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useNavigate } from "react-router-dom";
import { FaInfoCircle, FaPlus, FaTrash } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormSection } from "../../../ui/components/FormSection";
import { PageHeader } from "../../../ui/components/PageHeader";
import { usePmsAction } from "../api/hooks";

interface InventorDraft {
  user_id: number | "";
  name: string;
  email: string;
  department: string;
  ownership_percentage: number | string;
}

export default function SubmitApplicationPage() {
  const { session } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: "", abstract: "", detailed_description: "", claims: "", domain: "",
    jurisdiction: "IN", is_international: false, international_justification: "",
  });
  const [inventors, setInventors] = useState<InventorDraft[]>([{
    user_id: session?.user.id ?? "",
    name: session?.user.display_name ?? "",
    email: session?.user.email ?? "",
    department: "",
    ownership_percentage: 100,
  }]);
  const action = usePmsAction("post", () => "/applications/");
  const shareTotal = useMemo(
    () => inventors.reduce((sum, inventor) => sum + Number(inventor.ownership_percentage || 0), 0),
    [inventors],
  );
  const fieldsComplete = Boolean(
    form.title.trim() && form.abstract.trim() && form.detailed_description.trim()
    && form.claims.trim() && form.domain.trim()
    && (!form.is_international || form.international_justification.trim()),
  );
  const inventorsValid = inventors.every((inventor) =>
    inventor.name.trim() && inventor.email.trim() && Number(inventor.ownership_percentage) >= 0,
  ) && Math.abs(shareTotal - 100) < 0.01;

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((previous) => ({ ...previous, [key]: value }));
  }

  function updateInventor(index: number, key: keyof InventorDraft, value: string | number) {
    setInventors((previous) => previous.map((row, i) =>
      i === index ? { ...row, [key]: value } : row));
  }

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    action.mutate({
      ...form,
      coinventors: inventors.map((inventor) => ({
        ...inventor,
        user_id: inventor.user_id === "" ? null : Number(inventor.user_id),
        ownership_percentage: String(inventor.ownership_percentage),
      })),
    }, {
      onSuccess: () => {
        notifications.show({
          color: "green", title: "Application submitted",
          message: "PMS recorded the application. You can follow its status in My Applications.",
        });
        navigate("../mine");
      },
    });
  }

  return (
    <Container size="lg">
      <PageHeader title="Submit patent application" subtitle="Enter the invention details and inventor ownership information." />
      <Alert color="blue" variant="light" icon={<FaInfoCircle />} mb="md" title="Document files">
        The current PMS API does not accept binary document uploads at submission. This form does not mark files as uploaded; contact the PMS administrator for supporting document intake.
      </Alert>
      <Card padding="lg">
        <form onSubmit={submit}>
          <Stack gap="lg">
            <FormSection title="Invention" first hint="Required fields are validated again by PMS before submission.">
              <Stack gap="sm">
                <TextInput label="Title" required value={form.title} onChange={(e) => update("title", e.currentTarget.value)} />
                <TextInput label="Technology domain" required value={form.domain} onChange={(e) => update("domain", e.currentTarget.value)} />
                <Textarea label="Abstract" required minRows={3} autosize value={form.abstract} onChange={(e) => update("abstract", e.currentTarget.value)} />
                <Textarea label="Detailed description" required minRows={5} autosize value={form.detailed_description} onChange={(e) => update("detailed_description", e.currentTarget.value)} />
                <Textarea label="Claims" required minRows={4} autosize value={form.claims} onChange={(e) => update("claims", e.currentTarget.value)} />
                <Group grow align="flex-start">
                  <TextInput label="Jurisdiction" required value={form.jurisdiction} onChange={(e) => update("jurisdiction", e.currentTarget.value)} />
                  <label style={{ display: "flex", gap: 8, alignItems: "center", paddingTop: 28 }}>
                    <input type="checkbox" checked={form.is_international} onChange={(e) => update("is_international", e.currentTarget.checked)} />
                    <Text size="sm">International filing planned</Text>
                  </label>
                </Group>
                {form.is_international && (
                  <Textarea label="International filing justification" required minRows={2} autosize
                    value={form.international_justification}
                    onChange={(e) => update("international_justification", e.currentTarget.value)} />
                )}
              </Stack>
            </FormSection>

            <FormSection title="Inventors and ownership" hint="Ownership shares must total 100%.">
              <Stack gap="md">
                {inventors.map((inventor, index) => (
                  <Card key={index} withBorder padding="sm">
                    <Group justify="space-between" mb="xs">
                      <Text fw={600} size="sm">Inventor {index + 1}</Text>
                      {inventors.length > 1 && (
                        <Button size="xs" variant="subtle" color="red" leftSection={<FaTrash size={10} />}
                          onClick={() => setInventors((old) => old.filter((_, i) => i !== index))}>
                          Remove
                        </Button>
                      )}
                    </Group>
                    <Stack gap="xs">
                      <TextInput label="Name" required value={inventor.name}
                        onChange={(e) => updateInventor(index, "name", e.currentTarget.value)} />
                      <TextInput label="Email" type="email" required value={inventor.email}
                        onChange={(e) => updateInventor(index, "email", e.currentTarget.value)} />
                      <TextInput label="IAM user ID (if applicable)" type="number"
                        value={inventor.user_id} onChange={(e) => updateInventor(index, "user_id", e.currentTarget.value)} />
                      <TextInput label="Department" value={inventor.department}
                        onChange={(e) => updateInventor(index, "department", e.currentTarget.value)} />
                      <NumberInput label="Ownership percentage" min={0} max={100} decimalScale={2}
                        value={inventor.ownership_percentage}
                        onChange={(value) => updateInventor(index, "ownership_percentage", value)} />
                    </Stack>
                  </Card>
                ))}
                <Group justify="space-between">
                  <Button variant="default" leftSection={<FaPlus size={11} />}
                    onClick={() => setInventors((rows) => [...rows, {
                      user_id: "", name: "", email: "", department: "", ownership_percentage: 0,
                    }])}>
                    Add inventor
                  </Button>
                  <Text size="sm" c={Math.abs(shareTotal - 100) < 0.01 ? "green" : "red"}>
                    Ownership total: {shareTotal.toFixed(2)}%
                  </Text>
                </Group>
              </Stack>
            </FormSection>
            {action.error && <ErrorState error={action.error} />}
            <Group justify="flex-end">
              <Button type="submit" loading={action.isPending}
                disabled={!fieldsComplete || !inventors.length || !inventorsValid}>
                Submit application
              </Button>
            </Group>
          </Stack>
        </form>
      </Card>
    </Container>
  );
}
