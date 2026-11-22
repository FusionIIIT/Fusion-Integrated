import {
  Badge,
  Button,
  Card,
  Container,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { FaClock } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications } from "../api/hooks";
import type { PatentApplication } from "../types";

export default function MaintenancePage() {
  const { data: apps } = useApplications({ status: "granted" });

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Patent Annuity & Maintenance"
        subtitle="Manage annual maintenance renewals and fee disbursements for granted institute patents."
        icon={<FaClock size={28} />}
      />

      <Card shadow="xs" padding="lg" radius="md" withBorder mt="md">
        <Title order={4} mb="md">
          Granted Patents (Annuity Portfolio)
        </Title>
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Application No</Table.Th>
              <Table.Th>Grant Number</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Grant Date</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {apps?.map((app: PatentApplication) => (
              <Table.Tr key={app.id}>
                <Table.Td fw={600}>{app.application_no}</Table.Td>
                <Table.Td fw={700} c="green">{app.grant_number || "—"}</Table.Td>
                <Table.Td>{app.title}</Table.Td>
                <Table.Td>{app.grant_date || "—"}</Table.Td>
                <Table.Td>
                  <Badge color="green">Active Patent</Badge>
                </Table.Td>
                <Table.Td>
                  <Button size="xs" component={Link} to={`/pms/applications/${app.id}`}>
                    Annuity Schedule
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
            {(!apps || apps.length === 0) && (
              <Table.Tr>
                <Table.Td colSpan={6} style={{ textAlign: "center", color: "gray" }}>
                  No granted patents currently in post-grant maintenance portfolio.
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
