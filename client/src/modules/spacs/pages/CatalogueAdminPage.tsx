import { Button, Card, Container, Group, Text } from "@mantine/core";
import { FaPlus } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function CatalogueAdminPage() {
  return (
    <Container size="xl">
      <PageHeader
        title="Catalogue Administration"
        subtitle="Manage scholarship and award scheme policies, versioning, and effective dates"
        action={
          <Button leftSection={<FaPlus size={12} />}>
            New Scheme
          </Button>
        }
      />
      <Card withBorder shadow="sm" radius="md" p="md" mt="md">
        <Text c="dimmed" size="sm">
          Active catalogue items and draft versions will be listed here.
        </Text>
      </Card>
    </Container>
  );
}
