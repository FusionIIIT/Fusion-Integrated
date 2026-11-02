import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaFlask, FaCheckCircle, FaClock } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";

interface Proposal {
  id: number;
  title: string;
  pi_name: string;
  department: string;
  funding_agency: string;
  budget: number;
  status: string;
  start_date: string;
  end_date: string;
}

const INITIAL_PROPOSALS: Proposal[] = [
  {
    id: 1,
    title: "AI-Powered Renewable Energy Grid Forecasting",
    pi_name: "Dr. A. Sharma",
    department: "Computer Science & Engineering",
    funding_agency: "SERB / CRG",
    budget: 3500000,
    status: "APPROVED_DEAN",
    start_date: "2026-04-01",
    end_date: "2029-03-31",
  },
  {
    id: 2,
    title: "Advanced Composite Materials for Aerospace Systems",
    pi_name: "Dr. R. Verma",
    department: "Mechanical Engineering",
    funding_agency: "DRDO / ER&IPR",
    budget: 4800000,
    status: "VERIFIED_ADMIN",
    start_date: "2026-06-01",
    end_date: "2029-05-31",
  },
  {
    id: 3,
    title: "Sub-THz Waveguide Antennas for 6G Communication",
    pi_name: "Dr. K. Patel",
    department: "Electronics & Communication",
    funding_agency: "DST / MeitY",
    budget: 2800000,
    status: "SUBMITTED_HOD",
    start_date: "2026-08-01",
    end_date: "2028-07-31",
  },
];

function statusColor(status: string): string {
  switch (status) {
    case "APPROVED_DEAN":
    case "APPROVED_DIRECTOR":
      return "green";
    case "VERIFIED_ADMIN":
    case "RECOMMENDED_HOD":
      return "blue";
    case "SUBMITTED_HOD":
      return "yellow";
    case "REJECTED":
      return "red";
    default:
      return "gray";
  }
}

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<Proposal[]>(INITIAL_PROPOSALS);
  const [opened, { open, close }] = useDisclosure(false);

  // Form states
  const [title, setTitle] = useState("");
  const [piName, setPiName] = useState("");
  const [department, setDepartment] = useState("");
  const [agency, setAgency] = useState("");
  const [budget, setBudget] = useState<number | string>(1000000);
  const [objectives, setObjectives] = useState("");

  const handleSubmit = () => {
    if (!title || !piName || !department || !agency) {
      notifications.show({
        title: "Validation Error",
        message: "Please fill in all mandatory proposal fields.",
        color: "red",
      });
      return;
    }

    const newProposal: Proposal = {
      id: proposals.length + 1,
      title,
      pi_name: piName,
      department,
      funding_agency: agency,
      budget: Number(budget),
      status: "SUBMITTED_HOD",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: "2028-03-31",
    };

    setProposals([newProposal, ...proposals]);
    notifications.show({
      title: "Proposal Submitted",
      message: `Research proposal "${title}" submitted to HoD for review.`,
      color: "green",
    });

    setTitle("");
    setPiName("");
    setDepartment("");
    setAgency("");
    setObjectives("");
    close();
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Research Project Proposals"
        subtitle="Manage, review, and track institutional sponsored research proposals"
        action={
          <Button leftSection={<FaPlus />} onClick={open}>
            New Proposal
          </Button>
        }
      />

      <SimpleGrid cols={{ base: 1, sm: 3 }} mb="lg">
        <Card withBorder padding="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Total Proposals
            </Text>
            <FaFlask color="#1E3A8A" />
          </Group>
          <Title order={3} mt="sm">
            {proposals.length}
          </Title>
          <Text size="xs" c="dimmed" mt={4}>
            Sponsored projects portfolio
          </Text>
        </Card>

        <Card withBorder padding="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Approved Projects
            </Text>
            <FaCheckCircle color="#166534" />
          </Group>
          <Title order={3} mt="sm">
            {proposals.filter((p) => p.status.startsWith("APPROVED")).length}
          </Title>
          <Text size="xs" c="dimmed" mt={4}>
            Active sanctioned projects
          </Text>
        </Card>

        <Card withBorder padding="md" radius="md">
          <Group justify="space-between">
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Under Review
            </Text>
            <FaClock color="#CA8A04" />
          </Group>
          <Title order={3} mt="sm">
            {proposals.filter((p) => !p.status.startsWith("APPROVED")).length}
          </Title>
          <Text size="xs" c="dimmed" mt={4}>
            Awaiting review / verification
          </Text>
        </Card>
      </SimpleGrid>

      <Card withBorder radius="md">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Proposal Title</Table.Th>
              <Table.Th>PI / Department</Table.Th>
              <Table.Th>Funding Agency</Table.Th>
              <Table.Th>Sanctioned Budget</Table.Th>
              <Table.Th>Timeline</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {proposals.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>
                  <Text fw={600} size="sm">
                    {item.title}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{item.pi_name}</Text>
                  <Text size="xs" c="dimmed">
                    {item.department}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="light" color="indigo">
                    {item.funding_agency}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text fw={600} size="sm">
                    ₹{item.budget.toLocaleString("en-IN")}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed">
                    {item.start_date} to {item.end_date}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={statusColor(item.status)} variant="filled">
                    {item.status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={opened} onClose={close} title="Submit New Research Proposal" size="lg">
        <Stack gap="sm">
          <TextInput
            label="Project Title"
            placeholder="e.g. Next-Generation Sensor Architecture"
            required
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
          />
          <Group grow>
            <TextInput
              label="Principal Investigator Name"
              placeholder="Dr. Full Name"
              required
              value={piName}
              onChange={(e) => setPiName(e.currentTarget.value)}
            />
            <TextInput
              label="Department"
              placeholder="e.g. CSE / ECE / ME"
              required
              value={department}
              onChange={(e) => setDepartment(e.currentTarget.value)}
            />
          </Group>
          <Group grow>
            <TextInput
              label="Funding Agency"
              placeholder="e.g. SERB / DST / ISRO"
              required
              value={agency}
              onChange={(e) => setAgency(e.currentTarget.value)}
            />
            <NumberInput
              label="Proposed Budget (INR)"
              required
              value={budget}
              onChange={setBudget}
              min={10000}
            />
          </Group>
          <Textarea
            label="Key Objectives"
            placeholder="Describe the research scope and deliverables"
            rows={3}
            value={objectives}
            onChange={(e) => setObjectives(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={close}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>Submit Proposal</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
