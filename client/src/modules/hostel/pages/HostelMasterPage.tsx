import { useState } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  Table,
  Tabs,
  Textarea,
  TextInput,
  } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBuilding, FaTimes, FaUserShield } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateHostel,
  useCreateRoleBinding,
  useDeactivateRoleBinding,
  useHostels,
  useRoleBindings,
  useToggleHostelActive,
} from "../api/hooks";

export default function HostelMasterPage() {
  const { data: hostelsData, error: hostelsError } = useHostels();
  const { data: bindingsData } = useRoleBindings();

  const createHostel = useCreateHostel();
  const toggleActive = useToggleHostelActive();
  const createBinding = useCreateRoleBinding();
  const deactivateBinding = useDeactivateRoleBinding();

  const [hostelModalOpen, setHostelModalOpen] = useState(false);
  const [bindingModalOpen, setBindingModalOpen] = useState(false);

  // New hostel form state
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [capacity, setCapacity] = useState<number | string>(100);
  const [gender, setGender] = useState<string>("boys");
  const [description, setDescription] = useState("");

  // New role binding form state
  const [bindingHostelId, setBindingHostelId] = useState<string | null>(null);
  const [bindingUserId, setBindingUserId] = useState<number | string>(1);
  const [bindingRole, setBindingRole] = useState<string>("warden");
  const [bindingStartDate, setBindingStartDate] = useState(new Date().toISOString().slice(0, 10));

  const handleCreateHostel = async () => {
    try {
      await createHostel.mutateAsync({
        name,
        code,
        capacity: Number(capacity),
        gender: gender as any,
        description,
        is_active: true,
      });
      notifications.show({ title: "Success", message: "Hostel created successfully", color: "green" });
      setHostelModalOpen(false);
      setName("");
      setCode("");
      setDescription("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to create hostel", color: "red" });
    }
  };

  const handleCreateBinding = async () => {
    if (!bindingHostelId) return;
    try {
      await createBinding.mutateAsync({
        hostel: Number(bindingHostelId),
        user_id: Number(bindingUserId),
        role: bindingRole as any,
        start_date: bindingStartDate,
        is_active: true,
      });
      notifications.show({ title: "Success", message: "Staff role assigned successfully", color: "green" });
      setBindingModalOpen(false);
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to assign role", color: "red" });
    }
  };

  if (hostelsError) {
    return (
      <Container size="xl">
        <ErrorState error={hostelsError} />
      </Container>
    );
  }

  const hostels = hostelsData?.results ?? [];
  const bindings = bindingsData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Hostels & Administration"
        subtitle="Manage institute hostel premises, infrastructure, and administrative role bindings"
        action={
          <Group>
            <Button leftSection={<FaBuilding size={14} />} onClick={() => setHostelModalOpen(true)}>
              New Hostel
            </Button>
            <Button variant="light" leftSection={<FaUserShield size={14} />} onClick={() => setBindingModalOpen(true)}>
              Assign Staff Role
            </Button>
          </Group>
        }
      />

      <Tabs defaultValue="hostels" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="hostels" leftSection={<FaBuilding size={14} />}>
            Hostels Directory ({hostels.length})
          </Tabs.Tab>
          <Tabs.Tab value="roles" leftSection={<FaUserShield size={14} />}>
            Administrative Bindings ({bindings.length})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="hostels">
          <Card withBorder radius="md">
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Code</Table.Th>
                  <Table.Th>Name</Table.Th>
                  <Table.Th>Gender</Table.Th>
                  <Table.Th>Capacity</Table.Th>
                  <Table.Th>Total Rooms</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Active Toggle</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {hostels.map((h) => (
                  <Table.Tr key={h.id}>
                    <Table.Td fw={700}>{h.code}</Table.Td>
                    <Table.Td>{h.name}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline" color={h.gender === "girls" ? "pink" : "blue"}>
                        {h.gender.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{h.capacity} beds</Table.Td>
                    <Table.Td>{h.rooms_count ?? 0}</Table.Td>
                    <Table.Td>
                      <Badge color={h.is_active ? "green" : "gray"}>
                        {h.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      <Switch
                        checked={h.is_active}
                        onChange={(e) => toggleActive.mutate({ id: h.id, is_active: e.currentTarget.checked })}
                      />
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="roles">
          <Card withBorder radius="md">
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Hostel</Table.Th>
                  <Table.Th>User ID</Table.Th>
                  <Table.Th>Role</Table.Th>
                  <Table.Th>Start Date</Table.Th>
                  <Table.Th>End Date</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Action</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bindings.map((b) => (
                  <Table.Tr key={b.id}>
                    <Table.Td fw={600}>{b.hostel_name || `Hostel #${b.hostel}`}</Table.Td>
                    <Table.Td>User #{b.user_id}</Table.Td>
                    <Table.Td>
                      <Badge color={b.role === "warden" ? "indigo" : "teal"}>
                        {b.role.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{b.start_date}</Table.Td>
                    <Table.Td>{b.end_date || "Present"}</Table.Td>
                    <Table.Td>
                      <Badge color={b.is_active ? "green" : "gray"}>
                        {b.is_active ? "Active" : "Deactivated"}
                      </Badge>
                    </Table.Td>
                    <Table.Td>
                      {b.is_active && (
                        <ActionIcon
                          color="red"
                          variant="light"
                          onClick={() => deactivateBinding.mutate(b.id)}
                          title="Deactivate binding"
                        >
                          <FaTimes size={14} />
                        </ActionIcon>
                      )}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Modal: Create Hostel */}
      <Modal opened={hostelModalOpen} onClose={() => setHostelModalOpen(false)} title="Create New Hostel" centered>
        <Stack gap="sm">
          <TextInput label="Hostel Name" placeholder="e.g. Aryabhatta Hostel" required value={name} onChange={(e) => setName(e.target.value)} />
          <TextInput label="Hostel Code" placeholder="e.g. BH-1" required value={code} onChange={(e) => setCode(e.target.value)} />
          <NumberInput label="Total Student Capacity" min={1} required value={capacity} onChange={setCapacity} />
          <Select
            label="Gender Restriction"
            required
            data={[
              { value: "boys", label: "Boys" },
              { value: "girls", label: "Girls" },
              { value: "coed", label: "Co-ed" },
            ]}
            value={gender}
            onChange={(val) => val && setGender(val)}
          />
          <Textarea label="Description / Facilities" placeholder="Hostel facilities and location" value={description} onChange={(e) => setDescription(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setHostelModalOpen(false)}>Cancel</Button>
            <Button loading={createHostel.isPending} onClick={handleCreateHostel}>Save Hostel</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Assign Staff Role */}
      <Modal opened={bindingModalOpen} onClose={() => setBindingModalOpen(false)} title="Assign Administrative Role" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            placeholder="Select hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={bindingHostelId}
            onChange={setBindingHostelId}
          />
          <NumberInput label="User ID (IAM Principal)" required value={bindingUserId} onChange={setBindingUserId} />
          <Select
            label="Role Designation"
            required
            data={[
              { value: "warden", label: "Warden" },
              { value: "caretaker", label: "Caretaker" },
            ]}
            value={bindingRole}
            onChange={(val) => val && setBindingRole(val)}
          />
          <TextInput label="Start Date" type="date" required value={bindingStartDate} onChange={(e) => setBindingStartDate(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setBindingModalOpen(false)}>Cancel</Button>
            <Button loading={createBinding.isPending} onClick={handleCreateBinding}>Assign Role</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
