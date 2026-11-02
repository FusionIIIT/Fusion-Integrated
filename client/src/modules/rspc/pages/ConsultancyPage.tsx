import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { FaPlus, FaBriefcase } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";

interface Consultancy {
  id: number;
  title: string;
  pi_name: string;
  client_name: string;
  total_cost: number;
  institutional_share: number;
  status: string;
  start_date: string;
  end_date: string;
}

const INITIAL_CONSULTANCIES: Consultancy[] = [
  {
    id: 1,
    title: "Structural Health Assessment of Highway Bridges",
    pi_name: "Dr. P. Sen",
    client_name: "National Highways Authority of India (NHAI)",
    total_cost: 650000,
    institutional_share: 130000,
    status: "APPROVED_DEAN",
    start_date: "2026-03-01",
    end_date: "2026-09-30",
  },
  {
    id: 2,
    title: "Automated Visual Inspection for Manufacturing Lines",
    pi_name: "Dr. A. Sharma",
    client_name: "TATA Motors Ltd",
    total_cost: 850000,
    institutional_share: 170000,
    status: "RECOMMENDED_HOD",
    start_date: "2026-05-01",
    end_date: "2026-11-30",
  },
];

export default function ConsultancyPage() {
  const [consultancies, setConsultancies] = useState<Consultancy[]>(INITIAL_CONSULTANCIES);
  const [opened, { open, close }] = useDisclosure(false);

  const [title, setTitle] = useState("");
  const [client, setClient] = useState("");
  const [piName, setPiName] = useState("");
  const [cost, setCost] = useState<number | string>(500000);
  const [scope, setScope] = useState("");

  const handleSubmit = () => {
    if (!title || !client || !piName) {
      notifications.show({
        title: "Validation Error",
        message: "Please fill in all mandatory fields.",
        color: "red",
      });
      return;
    }

    const total = Number(cost);
    const newEntry: Consultancy = {
      id: consultancies.length + 1,
      title,
      pi_name: piName,
      client_name: client,
      total_cost: total,
      institutional_share: Math.round(total * 0.2),
      status: "SUBMITTED_HOD",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: "2026-12-31",
    };

    setConsultancies([newEntry, ...consultancies]);
    notifications.show({
      title: "Consultancy Registered",
      message: `Consultancy project "${title}" registered successfully.`,
      color: "green",
    });

    setTitle("");
    setClient("");
    setPiName("");
    setScope("");
    close();
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Consultancy Projects"
        subtitle="Industrial consultancy, professional testing services, and client deliverables"
        action={
          <Button leftSection={<FaPlus />} onClick={open}>
            Register Consultancy
          </Button>
        }
      />

      <Card withBorder radius="md">
        <Table verticalSpacing="sm" highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Project Title</Table.Th>
              <Table.Th>Faculty Consultant</Table.Th>
              <Table.Th>Client Organization</Table.Th>
              <Table.Th>Total Value</Table.Th>
              <Table.Th>Institute Share (20%)</Table.Th>
              <Table.Th>Status</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {consultancies.map((item) => (
              <Table.Tr key={item.id}>
                <Table.Td>
                  <Text fw={600} size="sm">
                    {item.title}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm">{item.pi_name}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge variant="light" color="cyan">
                    {item.client_name}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Text fw={600} size="sm">
                    ₹{item.total_cost.toLocaleString("en-IN")}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="teal" fw={600}>
                    ₹{item.institutional_share.toLocaleString("en-IN")}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Badge
                    color={item.status === "APPROVED_DEAN" ? "green" : "blue"}
                    variant="filled"
                  >
                    {item.status}
                  </Badge>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>

      <Modal opened={opened} onClose={close} title="Register New Consultancy Project">
        <Stack gap="sm">
          <TextInput
            label="Project Title"
            placeholder="e.g. Design Audit of Hydraulic Systems"
            required
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
          />
          <TextInput
            label="Client Organization"
            placeholder="Client Name & Address"
            required
            value={client}
            onChange={(e) => setClient(e.currentTarget.value)}
          />
          <TextInput
            label="Faculty Consultant (PI)"
            placeholder="Faculty Name"
            required
            value={piName}
            onChange={(e) => setPiName(e.currentTarget.value)}
          />
          <NumberInput
            label="Total Agreed Cost (INR)"
            required
            value={cost}
            onChange={setCost}
            min={10000}
          />
          <Textarea
            label="Scope & Deliverables"
            placeholder="Deliverables description"
            rows={3}
            value={scope}
            onChange={(e) => setScope(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={close}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>Register Project</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
