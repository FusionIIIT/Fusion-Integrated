import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { Link, useNavigate } from "react-router-dom";
import { FaCertificate, FaPlus, FaSearch } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications, usePmsReportSummary } from "../api/hooks";
import type { PatentApplication } from "../types";

export default function PMSDashboardPage() {
  const navigate = useNavigate();
  const { data: apps, isPending: appsLoading } = useApplications();
  const { data: summary } = usePmsReportSummary();

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Patent Management System"
        subtitle="Manage institute patent applications, scrutiny reviews, filings, and maintenance."
        icon={<FaCertificate size={28} />}
        actions={
          <Button
            component={Link}
            to="/pms/applications/new"
            leftSection={<FaPlus />}
            color="blue"
          >
            New Patent Draft
          </Button>
        }
      />

      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="lg">
        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
            Total Applications
          </Text>
          <Text size="xl" fw={700} mt="xs">
            {(summary?.total_applications as number) ?? apps?.length ?? 0}
          </Text>
        </Card>
        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
            Under Review
          </Text>
          <Text size="xl" fw={700} mt="xs" c="orange">
            {(summary?.pending_internal_review as number) ?? 0}
          </Text>
        </Card>
        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
            Externally Filed
          </Text>
          <Text size="xl" fw={700} mt="xs" c="blue">
            {(summary?.total_externally_filed as number) ?? 0}
          </Text>
        </Card>
        <Card shadow="xs" padding="lg" radius="md" withBorder>
          <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
            Granted Patents
          </Text>
          <Text size="xl" fw={700} mt="xs" c="green">
            {(summary?.total_granted as number) ?? 0}
          </Text>
        </Card>
      </SimpleGrid>

      <Card shadow="xs" padding="md" radius="md" withBorder>
        <Title order={4} mb="md">
          Active Patent Applications
        </Title>
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Tracking ID</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Filing Type</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Created Date</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {apps?.map((app: PatentApplication) => (
              <Table.Tr
                key={app.id}
                style={{ cursor: "pointer" }}
                onClick={() => navigate(`/pms/applications/${app.id}`)}
              >
                <Table.Td fw={600}>{app.application_no}</Table.Td>
                <Table.Td>{app.title}</Table.Td>
                <Table.Td tt="capitalize">{app.filing_type}</Table.Td>
                <Table.Td>
                  <Badge
                    color={
                      app.status === "granted"
                        ? "green"
                        : app.status === "rejected"
                        ? "red"
                        : app.status === "under_review"
                        ? "orange"
                        : "blue"
                    }
                  >
                    {app.status}
                  </Badge>
                </Table.Td>
                <Table.Td>{new Date(app.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td>
                  <Button size="xs" variant="light">
                    View Lifecycle
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
            {(!apps || apps.length === 0) && (
              <Table.Tr>
                <Table.Td colSpan={6} style={{ textAlign: "center", color: "gray" }}>
                  No patent applications found. Click &quot;New Patent Draft&quot; to begin.
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
