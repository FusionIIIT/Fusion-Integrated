import { useEffect, useState } from "react";
import { Badge, Card, Container, Table, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import { rspcApi } from "../api/client";
import type { Project } from "../api/types";

export default function ProjectsListPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const res = await rspcApi.getProjects();
      setProjects(res.data);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to load projects";
      notifications.show({ color: "red", message: msg });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Sponsored Projects"
        subtitle="Manage active grants, sanction records, extension requests and milestone progress"
      />

      <Card withBorder shadow="sm" radius="md" mt="md">
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Code</Table.Th>
              <Table.Th>Project Title</Table.Th>
              <Table.Th>Department</Table.Th>
              <Table.Th>Funding Agency</Table.Th>
              <Table.Th>Sanctioned Amount</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {loading ? (
              <Table.Tr>
                <Table.Td colSpan={6} style={{ textAlign: "center", padding: "2rem" }}>
                  <Text c="dimmed">Loading projects...</Text>
                </Table.Td>
              </Table.Tr>
            ) : projects.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={6} style={{ textAlign: "center", padding: "2rem" }}>
                  <Text c="dimmed">No active or sanctioned projects found.</Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              projects.map((p) => (
                <Table.Tr key={p.id}>
                  <Table.Td fw={700}>{p.project_code}</Table.Td>
                  <Table.Td>{p.title}</Table.Td>
                  <Table.Td>{p.department}</Table.Td>
                  <Table.Td>{p.funding_agency}</Table.Td>
                  <Table.Td>₹{Number(p.sanctioned_amount).toLocaleString("en-IN")}</Table.Td>
                  <Table.Td>
                    <Badge color={p.status === "active" ? "green" : "blue"}>{p.status}</Badge>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
