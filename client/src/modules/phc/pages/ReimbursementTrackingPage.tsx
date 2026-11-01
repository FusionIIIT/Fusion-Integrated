import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Drawer,
  Stack,
  Table,
  Text,
  Timeline,
  Title,
} from "@mantine/core";
import { FaHistory, FaPlus } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useMyReimbursements } from "../api/hooks";
import type { ReimbursementClaim } from "../api/types";

function getStatusBadge(status: string) {
  switch (status) {
    case "Pending PHC Review":
      return <Badge color="blue" variant="light">1. Pending PHC Review</Badge>;
    case "Pending Accounts Verification":
      return <Badge color="indigo" variant="light">2. Pending Accounts Verification</Badge>;
    case "Pending Sanction":
      return <Badge color="orange" variant="light">3. Pending Sanction</Badge>;
    case "Approved for Payment":
      return <Badge color="teal" variant="light">4. Approved for Payment</Badge>;
    case "Reimbursed":
      return <Badge color="green" variant="filled">5. Reimbursed</Badge>;
    case "Rejected":
      return <Badge color="red" variant="filled">Rejected (Terminal)</Badge>;
    default:
      return <Badge color="gray">{status}</Badge>;
  }
}

export default function ReimbursementTrackingPage() {
  const navigate = useNavigate();
  const { data: claims, isPending, error } = useMyReimbursements();
  const [selectedClaim, setSelectedClaim] = useState<ReimbursementClaim | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  if (error) return <ErrorState error={error} />;

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="My Reimbursement Claims"
        subtitle="Track workflow progression and recorded action history (AFR-PHC-022; PHC-BR-08, 14)"
        action={
          <Button leftSection={<FaPlus />} color="blue" onClick={() => navigate("/phc/reimbursement/apply")}>
            New Claim
          </Button>
        }
      />

      <Card withBorder p="sm" mb="md" bg="blue.0">
        <Text size="xs" c="blue.9">
          Policy Note (PHC-BR-14): Submitted and rejected reimbursement claims are immutable workflow instances.
          If any changes are required or if re-applying after rejection, a new claim application must be submitted.
        </Text>
      </Card>

      {isPending ? (
        <Text c="dimmed">Loading your claims...</Text>
      ) : !claims || claims.length === 0 ? (
        <Card withBorder p="xl">
          <Text c="dimmed" ta="center">
            You have not submitted any medical bill reimbursement claims.
          </Text>
        </Card>
      ) : (
        <Table striped highlightOnHover withTableBorder>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Claim #</Table.Th>
              <Table.Th>Submitted On</Table.Th>
              <Table.Th>Expense Date</Table.Th>
              <Table.Th>Prescription #</Table.Th>
              <Table.Th>Claimed</Table.Th>
              <Table.Th>Sanctioned</Table.Th>
              <Table.Th>Current State</Table.Th>
              <Table.Th>Action History</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {claims.map((claim) => (
              <Table.Tr key={claim.id}>
                <Table.Td fw={600}>{claim.claim_number}</Table.Td>
                <Table.Td>{new Date(claim.created_at).toLocaleDateString()}</Table.Td>
                <Table.Td>{claim.expense_date}</Table.Td>
                <Table.Td>
                  <Badge variant="outline" color="blue">
                    {claim.prescription_number}
                  </Badge>
                </Table.Td>
                <Table.Td fw={500}>₹{claim.amount_claimed}</Table.Td>
                <Table.Td fw={600} c={claim.amount_approved ? "teal" : "dimmed"}>
                  {claim.amount_approved ? `₹${claim.amount_approved}` : "—"}
                </Table.Td>
                <Table.Td>{getStatusBadge(claim.status)}</Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    leftSection={<FaHistory />}
                    variant="light"
                    onClick={() => {
                      setSelectedClaim(claim);
                      setDrawerOpen(true);
                    }}
                  >
                    View History
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* History Drawer */}
      <Drawer
        opened={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={selectedClaim ? `Lifecycle History: ${selectedClaim.claim_number}` : "Claim History"}
        position="right"
        size="md"
      >
        {selectedClaim && (
          <Stack gap="md">
            <Card withBorder p="md" bg="gray.0">
              <Text fw={600}>Claim Amount: ₹{selectedClaim.amount_claimed}</Text>
              <Text size="xs" c="dimmed">
                Status: {selectedClaim.status}
              </Text>
              {selectedClaim.remarks && (
                <Text size="xs" mt={4}>
                  Remarks: {selectedClaim.remarks}
                </Text>
              )}
            </Card>

            <Title order={5}>Audit Timeline (CW-PHC-01)</Title>
            <Timeline active={(selectedClaim.history?.length ?? 1) - 1} bulletSize={22} lineWidth={2}>
              {selectedClaim.history?.map((h) => (
                <Timeline.Item key={h.id} title={h.action}>
                  <Text c="dimmed" size="xs">
                    {h.from_status} → {h.to_status}
                  </Text>
                  <Text size="xs" fw={500}>
                    By: {h.actor_role} (User {h.actor_user_id})
                  </Text>
                  {h.comments && (
                    <Text size="xs" fs="italic" c="gray.7">
                      "{h.comments}"
                    </Text>
                  )}
                  <Text size="xs" c="dimmed" mt={2}>
                    {new Date(h.created_at).toLocaleString()}
                  </Text>
                </Timeline.Item>
              ))}
            </Timeline>
          </Stack>
        )}
      </Drawer>
    </Container>
  );
}
