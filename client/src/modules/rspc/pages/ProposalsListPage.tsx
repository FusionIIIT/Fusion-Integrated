import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  NumberInput,
  Select,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { useAuth } from "../../../auth/AuthProvider";
import {
  useCreateProposal,
  useProposals,
  useSubmitProposal,
} from "../api/hooks";
import { errorMessage } from "../../../lib/http";

export default function ProposalsListPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [agency, setAgency] = useState("");
  const [budget, setBudget] = useState<number | string>(100000);
  const [dept, setDept] = useState("CSE");
  const [summary, setSummary] = useState("");
  const { can } = useAuth();

  const { data: proposals, isLoading, error } = useProposals();
  const createMutation = useCreateProposal();
  const submitMutation = useSubmitProposal();

  const handleCreate = async () => {
    try {
      await createMutation.mutateAsync({
        title,
        funding_agency: agency,
        proposed_budget: String(budget),
        department: dept,
        summary,
        proposal_type: "sponsored_research",
      });
      notifications.show({ color: "green", message: "Proposal drafted successfully!" });
      setModalOpen(false);
      setTitle("");
      setAgency("");
      setSummary("");
    } catch (e) {
      notifications.show({ color: "red", message: errorMessage(e) });
    }
  };

  const handleSubmit = async (id: number) => {
    try {
      await submitMutation.mutateAsync(id);
      notifications.show({ color: "green", message: "Proposal submitted to HoD!" });
    } catch (e) {
      notifications.show({ color: "red", message: errorMessage(e) });
    }
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Research Proposals"
        subtitle="Submit and track funded project proposals through multi-stage institutional endorsement"
        action={
          can("rspc.proposal.create") && (
            <Button onClick={() => setModalOpen(true)}>New Proposal</Button>
          )
        }
      />

      {error ? (
        <Stack mt="md">
          <ErrorState error={error} />
        </Stack>
      ) : (
        <Card withBorder shadow="sm" radius="md" mt="md">
          <Table highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Title</Table.Th>
                <Table.Th>Agency</Table.Th>
                <Table.Th>Budget</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {isLoading ? (
                <Table.Tr>
                  <Table.Td colSpan={6} style={{ textAlign: "center", padding: "2rem" }}>
                    <Text c="dimmed">Loading proposals...</Text>
                  </Table.Td>
                </Table.Tr>
              ) : !proposals || proposals.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={6} style={{ textAlign: "center", padding: "2rem" }}>
                    <Text c="dimmed">No proposals found.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                proposals.map((p) => (
                  <Table.Tr key={p.id}>
                    <Table.Td>#{p.id}</Table.Td>
                    <Table.Td fw={500}>{p.title}</Table.Td>
                    <Table.Td>{p.funding_agency}</Table.Td>
                    <Table.Td>₹{Number(p.proposed_budget).toLocaleString("en-IN")}</Table.Td>
                    <Table.Td>
                      <Badge
                        color={
                          p.status === "approved_dean"
                            ? "green"
                            : p.status === "draft"
                            ? "gray"
                            : "blue"
                        }
                      >
                        {p.status}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {p.status === "draft" && can("rspc.proposal.create") && (
                        <Button
                          size="xs"
                          variant="light"
                          loading={submitMutation.isPending}
                          onClick={() => handleSubmit(p.id)}
                        >
                          Submit
                        </Button>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      <Modal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Draft New Research Proposal"
        centered
      >
        <Stack gap="md">
          <TextInput
            label="Proposal Title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
          <TextInput
            label="Funding Agency"
            required
            value={agency}
            onChange={(e) => setAgency(e.target.value)}
          />
          <Select
            label="Department"
            data={["CSE", "ECE", "ME", "Design", "Natural Sciences"]}
            value={dept}
            onChange={(v) => setDept(v || "CSE")}
          />
          <NumberInput
            label="Proposed Budget (INR)"
            required
            value={budget}
            onChange={setBudget}
            min={1000}
          />
          <Textarea
            label="Project Executive Summary"
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button loading={createMutation.isPending} onClick={handleCreate}>
              Save Draft
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
