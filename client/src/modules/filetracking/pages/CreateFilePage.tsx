import { Button, Card, Container, Stack, TextInput, Textarea } from "@mantine/core";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function CreateFilePage() {
  return (
    <Container size="xl" py="lg">
      <PageHeader
        title="Create New File"
        subtitle="Draft a new institutional file with mandatory initial comment"
      />
      <Stack mt="md">
        <Card withBorder p="md" radius="sm">
          <TextInput label="Subject" placeholder="Enter file subject" required mb="sm" />
          <Textarea label="Description" placeholder="Optional description" mb="sm" />
          <Textarea label="Initial Comment" placeholder="Mandatory initial comment (BR-FTS-004)" required mb="md" />
          <Button color="blue">Save as Draft</Button>
        </Card>
      </Stack>
    </Container>
  );
}
