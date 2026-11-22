import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { FaClipboardCheck } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { useApplications } from "../api/hooks";
import type { PatentApplication } from "../types";

export default function ReviewsPage() {
  const { data: apps, isPending } = useApplications({ status: "under_review" });

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Scrutiny & Reviews"
        subtitle="Review applications pending institutional patentability, novelty, and commercial evaluation."
        icon={<FaClipboardCheck size={28} />}
      />

      <Card shadow="xs" padding="lg" radius="md" withBorder mt="md">
        <Title order={4} mb="md">
          Applications Pending Scrutiny
        </Title>
        <Table highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Application No</Table.Th>
              <Table.Th>Title</Table.Th>
              <Table.Th>Applicant</Table.Th>
              <Table.Th>Filing Type</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Action</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {apps?.map((app: PatentApplication) => (
              <Table.Tr key={app.id}>
                <Table.Td fw={600}>{app.application_no}</Table.Td>
                <Table.Td>{app.title}</Table.Td>
                <Table.Td>User #{app.applicant_user_id}</Table.Td>
                <Table.Td tt="capitalize">{app.filing_type}</Table.Td>
                <Table.Td>
                  <Badge color="orange">{app.status}</Badge>
                </Table.Td>
                <Table.Td>
                  <Button size="xs" component={Link} to={`/pms/applications/${app.id}`}>
                    Conduct Evaluation
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
            {(!apps || apps.length === 0) && (
              <Table.Tr>
                <Table.Td colSpan={6} style={{ textAlign: "center", color: "gray" }}>
                  No applications currently awaiting review.
                </Table.Td>
              </Table.Tr>
            )}
          </Table.Tbody>
        </Table>
      </Card>
    </Container>
  );
}
