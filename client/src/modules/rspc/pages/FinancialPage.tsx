import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaCoins } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";

interface FinancialItem {
  id: number;
  project_title: string;
  budget_head: string;
  amount: number;
  purpose: string;
  status: string;
}

const INITIAL_FINANCIAL: FinancialItem[] = [
  {
    id: 1,
    project_title: "AI-Powered Renewable Energy Grid Forecasting",
    budget_head: "Consumables & Hardware",
    amount: 145000,
    purpose: "Edge computing developer kit and sensors",
    status: "APPROVED_DEAN",
  },
  {
    id: 2,
    project_title: "Advanced Composite Materials for Aerospace Systems",
    budget_head: "Travel & Field Study",
    amount: 85000,
    purpose: "Visit to testing facility at ISRO Bangalore",
    status: "VERIFIED_ADMIN",
  },
];

export default function FinancialPage() {
  const [requests, setRequests] = useState<FinancialItem[]>(INITIAL_FINANCIAL);
  const [opened, { open, close }] = useDisclosure(false);

  const [project, setProject] = useState("");
  const [head, setHead] = useState<string | null>("Consumables");
  const [amount, setAmount] = useState<number | string>(50000);
  const [purpose, setPurpose] = useState("");

  const handleSubmit = () => {
    if (!project || !purpose) {
      notifications.show({
        title: "Validation Error",
        message: "Please fill in all mandatory fields.",
        color: "red",
      });
      return;
    }

    const amt = Number(amount);
    const newReq: FinancialItem = {
      id: requests.length + 1,
      project_title: project,
      budget_head: head || "Consumables",
      amount: amt,
      purpose,
      status: "SUBMITTED",
    };

    setRequests([newReq, ...requests]);
    notifications.show({
      title: "Request Submitted",
      message: `Fund request for ₹${amt.toLocaleString("en-IN")} submitted for scrutiny.`,
      color: "green",
    });

    setProject("");
    setPurpose("");
    close();
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Fund & Financial Requests"
        subtitle="Submit expenditure requests, track utilization, and view Dean/Director approvals"
        action={
          <Button leftSection={<FaPlus />} onClick={open}>
            New Fund Request
          </Button>
        }
      />

      <Card withBorder radius="md">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Project</Table.Th>
              <Table.Th>Budget Head</Table.Th>
              <Table.Th>Requested Amount</Table.Th>
              <Table.Th>Purpose</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {requests.map((r) => (
              <Table.Tr key={r.id}>
                <Table.Td>
                  <Text fw={600} size="sm">
                    {r.project_title}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="outline">{r.budget_head}</Badge>
                </Table.Td>
                <Table.Td>
                  <Text fw={600} size="sm">
                    ₹{r.amount.toLocaleString("en-IN")}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{r.purpose}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge
                    color={r.status === "APPROVED_DEAN" ? "green" : "blue"}
                    variant="filled"
                  >
                    {r.status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={opened} onClose={close} title="Submit Fund Utilization Request">
        <Stack gap="sm">
          <TextInput
            label="Project Title"
            placeholder="Select or enter project"
            required
            value={project}
            onChange={(e) => setProject(e.currentTarget.value)}
          />
          <Select
            label="Budget Head"
            data={["Consumables", "Travel", "Equipment", "Contingency", "Manpower"]}
            value={head}
            onChange={setHead}
          />
          <NumberInput
            label="Amount (INR)"
            required
            value={amount}
            onChange={setAmount}
            min={1000}
          />
          <TextInput
            label="Purpose of Expenditure"
            placeholder="Justification and breakdown"
            required
            value={purpose}
            onChange={(e) => setPurpose(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={close}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>Submit Request</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
