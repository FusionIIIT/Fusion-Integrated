import { Badge, Card, Container, Group, Stack, Text, Title } from "@mantine/core";

import { useDepartmentInfo } from "../api/hooks";

export default function DepartmentDetailsPage() {
  const { data: dept, isLoading } = useDepartmentInfo();

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="lg">
        <div>
          <Title order={2}>Department Overview & Governance</Title>
          <Text c="dimmed">Official departmental policies, identity, and active headship</Text>
        </div>
      </Group>

      {isLoading && <Text>Loading department information...</Text>}

      {dept && (
        <Stack gap="lg">
          <Card withBorder shadow="sm" radius="md">
            <Title order={3} mb="xs">{dept.name} ({dept.code})</Title>
            <Text mb="md">{dept.description || "General academic and research department."}</Text>
            <Group gap="xl">
              <div>
                <Text size="xs" c="dimmed" fw={700}>HEAD OF DEPARTMENT (HOD)</Text>
                <Badge size="lg" color="blue" mt={4}>
                  {dept.head_of_department_id || "No Active HOD Assigned"}
                </Badge>
              </div>
              <div>
                <Text size="xs" c="dimmed" fw={700}>DEPARTMENT ADMINISTRATOR</Text>
                <Badge size="lg" color="teal" mt={4}>
                  {dept.department_admin_id || "No Active Admin Assigned"}
                </Badge>
              </div>
            </Group>
          </Card>

          <Card withBorder shadow="sm" radius="md">
            <Title order={4} mb="xs">Core Department Policies</Title>
            <Text style={{ whiteSpace: "pre-wrap" }}>
              {dept.core_policies || "Standard institute academic guidelines and regulations apply."}
            </Text>
          </Card>
        </Stack>
      )}
    </Container>
  );
}
