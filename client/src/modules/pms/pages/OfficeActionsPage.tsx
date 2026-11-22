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
import { FaFileText } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications } from "../api/hooks";
import type { PatentApplication } from "../types";

export default function OfficeActionsPage() {
  const { data: apps } = useApplications();

  // Filter applications with active office actions / examination reports
  const activeProsecution = apps?.filter((a) =>
    ["filed", "fer_received", "fer_responded", "hearing_scheduled"].includes(a.status)
  );

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Office Actions & Examination Reports"
        subtitle="Track statutory communications, First Examination Reports (FER), and responses."
        icon={<FaFileText size={28} />}
      />

      <Card shadow="xs" padding="lg" radius="md" withBorder mt="md">
        <Title order={4} mb="md">
          Active Patent Prosecution
        </Title>
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Application No</Table.Th>
              <Table.Th>Official Filing No</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Assigned Attorney</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {activeProsecution?.map((app: PatentApplication) => (
              <Table.Tr key={app.id}>
                <Table.Td fw={600}>{app.application_no}</Table.Td>
                <Table.Td>{app.official_filing_number || "Pending IPO assignment"}</Table.Td>
                <Table.Td>{app.title}</Table.Td>
                <Table.Td>
                  <Badge color="blue">{app.status}</Badge>
                </Table.Td>
                <Table.Td>
                  {app.assigned_attorney_id ? `Attorney #${app.assigned_attorney_id}` : "Unassigned"}
                </Table.Td>
                <Table.Td>
                  <Button size="xs" component={Link} to={`/pms/applications/${app.id}`}>
                    Manage Prosecution
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
            {(!activeProsecution || activeProsecution.length === 0) && (
              <Table.Tr>
                <Table.Td colSpan={6} style={{ textAlign: "center", color: "gray" }}>
                  No applications currently undergoing external examination prosecution.
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
