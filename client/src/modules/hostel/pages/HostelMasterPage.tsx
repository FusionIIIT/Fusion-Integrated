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
  Switch,
  Tabs,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { FaPlus, FaBuilding, FaUserShield, FaBed } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useCreateHostel,
  useCreateRoleBinding,
  useCreateRoom,
  useHostels,
  useRoleBindings,
  useRooms,
  useToggleHostelActive,
} from "../api/hooks";
import type { Hostel, HostelRoleBinding, Room } from "../api/types";

export default function HostelMasterPage() {
  const { can } = useAuth();
  const { data: hostels, isPending: hostelsPending, error: hostelsError } = useHostels();
  const { data: bindings, isPending: bindingsPending } = useRoleBindings();
  const { data: rooms, isPending: roomsPending } = useRooms();

  const createHostel = useCreateHostel();
  const toggleActive = useToggleHostelActive();
  const createBinding = useCreateRoleBinding();
  const createRoom = useCreateRoom();

  const [activeTab, setActiveTab] = useState<string | null>("hostels");
  const [hostelModalOpen, setHostelModalOpen] = useState(false);
  const [bindingModalOpen, setBindingModalOpen] = useState(false);
  const [roomModalOpen, setRoomModalOpen] = useState(false);

  // Form states
  const [hName, setHName] = useState("");
  const [hCode, setHCode] = useState("");
  const [hGender, setHGender] = useState<"boys" | "girls" | "coed">("coed");
  const [hCap, setHCap] = useState<number | string>(100);
  const [hDesc, setHDesc] = useState("");

  const [bHostelId, setBHostelId] = useState<string | null>(null);
  const [bUserId, setBUserId] = useState<number | string>(1);
  const [bRole, setBRole] = useState<string | null>("caretaker");
  const [bNotes, setBNotes] = useState("");

  const [rHostelId, setRHostelId] = useState<string | null>(null);
  const [rNumber, setRNumber] = useState("");
  const [rFloor, setRFloor] = useState<number | string>(1);
  const [rCap, setRCap] = useState<number | string>(2);
  const [rType, setRType] = useState<string | null>("double");

  if (hostelsError) {
    return (
      <Container size="xl">
        <ErrorState error={hostelsError} />
      </Container>
    );
  }

  const handleCreateHostel = async () => {
    if (!hName || !hCode) return;
    await createHostel.mutateAsync({
      name: hName,
      code: hCode,
      gender_policy: hGender,
      capacity: Number(hCap),
      description: hDesc,
      is_active: true,
    });
    setHostelModalOpen(false);
    setHName("");
    setHCode("");
    setHDesc("");
  };

  const handleCreateBinding = async () => {
    if (!bHostelId || !bRole) return;
    await createBinding.mutateAsync({
      hostel_id: Number(bHostelId),
      user_id: Number(bUserId),
      role: bRole,
      notes: bNotes,
      is_active: true,
    });
    setBindingModalOpen(false);
    setBNotes("");
  };

  const handleCreateRoom = async () => {
    if (!rHostelId || !rNumber) return;
    await createRoom.mutateAsync({
      hostel_id: Number(rHostelId),
      room_number: rNumber,
      floor: Number(rFloor),
      capacity: Number(rCap),
      room_type: rType || "double",
    });
    setRoomModalOpen(false);
    setRNumber("");
  };

  const hostelOptions = (hostels ?? []).map((h) => ({
    value: String(h.id),
    label: `${h.name} (${h.code})`,
  }));

  return (
    <Container size="xl">
      <PageHeader
        title="Hostel Master Administration"
        subtitle="Manage institute residences, staff role bindings, and room inventory"
        action={
          <Group gap="xs">
            {can("hostel.master.manage") && (
              <Button leftSection={<FaPlus size={12} />} onClick={() => setHostelModalOpen(true)}>
                New Hostel
              </Button>
            )}
            {can("hostel.role_binding.manage") && (
              <Button leftSection={<FaPlus size={12} />} variant="light" onClick={() => setBindingModalOpen(true)}>
                Assign Role
              </Button>
            )}
            {can("hostel.room.manage") && (
              <Button leftSection={<FaPlus size={12} />} variant="outline" onClick={() => setRoomModalOpen(true)}>
                Add Room
              </Button>
            )}
          </Group>
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab} mb="lg">
        <Tabs.List>
          <Tabs.Tab value="hostels" leftSection={<FaBuilding size={14} />}>
            Hostels ({hostels?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="bindings" leftSection={<FaUserShield size={14} />}>
            Role Bindings ({bindings?.length ?? 0})
          </Tabs.Tab>
          <Tabs.Tab value="rooms" leftSection={<FaBed size={14} />}>
            Rooms Inventory ({rooms?.length ?? 0})
          </Tabs.Tab>
        </Tabs.List>

        {/* HOSTELS TAB */}
        <Tabs.Panel value="hostels" pt="md">
          <Card withBorder padding="md">
            <DataTable<Hostel>
              rows={hostels ?? []}
              loading={hostelsPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "name", header: "Hostel Name", render: (r) => <Text fw={600}>{r.name}</Text> },
                { key: "code", header: "Code", render: (r) => <Badge variant="light">{r.code}</Badge> },
                { key: "policy", header: "Policy", render: (r) => r.gender_policy.toUpperCase() },
                { key: "capacity", header: "Capacity", render: (r) => r.capacity },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => (
                    <Badge color={r.is_active ? "teal" : "gray"}>
                      {r.is_active ? "Active" : "Inactive"}
                    </Badge>
                  ),
                },
                {
                  key: "actions",
                  header: "Actions",
                  render: (r) =>
                    can("hostel.master.manage") ? (
                      <Switch
                        size="sm"
                        checked={r.is_active}
                        onChange={(e) => toggleActive.mutate({ id: r.id, is_active: e.currentTarget.checked })}
                      />
                    ) : null,
                },
              ]}
              empty={{
                title: "No Hostels Defined",
                description: "Click 'New Hostel' above to create master hostel records.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* ROLE BINDINGS TAB */}
        <Tabs.Panel value="bindings" pt="md">
          <Card withBorder padding="md">
            <DataTable<HostelRoleBinding>
              rows={bindings ?? []}
              loading={bindingsPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "hostel", header: "Hostel", render: (r) => r.hostel_name },
                { key: "role", header: "Role", render: (r) => <Badge color="indigo">{r.role.toUpperCase()}</Badge> },
                { key: "user_id", header: "User ID", render: (r) => r.user_id },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => (
                    <Badge color={r.is_active ? "teal" : "gray"}>
                      {r.is_active ? "Active" : "Inactive"}
                    </Badge>
                  ),
                },
                { key: "start_date", header: "Start Date", render: (r) => r.start_date || "—" },
                { key: "end_date", header: "End Date", render: (r) => r.end_date || "—" },
                { key: "notes", header: "Notes", render: (r) => r.notes || "—" },
              ]}
              empty={{
                title: "No Role Bindings",
                description: "Assign wardens or caretakers to hostels above.",
              }}
            />
          </Card>
        </Tabs.Panel>

        {/* ROOMS TAB */}
        <Tabs.Panel value="rooms" pt="md">
          <Card withBorder padding="md">
            <DataTable<Room>
              rows={rooms ?? []}
              loading={roomsPending}
              rowKey={(r) => r.id}
              columns={[
                { key: "hostel", header: "Hostel", render: (r) => r.hostel_name },
                { key: "room", header: "Room #", render: (r) => <Text fw={600}>{r.room_number}</Text> },
                { key: "floor", header: "Floor", render: (r) => r.floor },
                { key: "type", header: "Type", render: (r) => r.room_type },
                {
                  key: "capacity",
                  header: "Capacity",
                  render: (r) => `${r.current_occupancy} / ${r.capacity}`,
                },
                {
                  key: "beds",
                  header: "Available Beds",
                  render: (r) => (
                    <Badge color={r.available_beds > 0 ? "teal" : "red"}>
                      {r.available_beds} beds free
                    </Badge>
                  ),
                },
              ]}
              empty={{
                title: "No Rooms Registered",
                description: "Add rooms to hostel wings and floors using the button above.",
              }}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Modal: Create Hostel */}
      <Modal opened={hostelModalOpen} onClose={() => setHostelModalOpen(false)} title="Create Master Hostel Record">
        <Stack gap="sm">
          <TextInput
            label="Hostel Name"
            placeholder="e.g. Hall of Residence 4"
            required
            value={hName}
            onChange={(e) => setHName(e.target.value)}
          />
          <TextInput
            label="Hostel Code"
            placeholder="e.g. HALL-4"
            required
            value={hCode}
            onChange={(e) => setHCode(e.target.value)}
          />
          <Select
            label="Gender Policy"
            data={[
              { value: "boys", label: "Boys Hostel" },
              { value: "girls", label: "Girls Hostel" },
              { value: "coed", label: "Co-Ed / Mixed" },
            ]}
            value={hGender}
            onChange={(v) => setHGender((v as "boys" | "girls" | "coed") || "coed")}
          />
          <NumberInput
            label="Total Capacity"
            min={1}
            value={hCap}
            onChange={setHCap}
          />
          <Textarea
            label="Description"
            placeholder="Location, wings, and features..."
            value={hDesc}
            onChange={(e) => setHDesc(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setHostelModalOpen(false)}>Cancel</Button>
            <Button loading={createHostel.isPending} onClick={handleCreateHostel}>Save Hostel</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Assign Role Binding */}
      <Modal opened={bindingModalOpen} onClose={() => setBindingModalOpen(false)} title="Assign Hostel Role Binding">
        <Stack gap="sm">
          <Select
            label="Hostel"
            placeholder="Select hostel"
            data={hostelOptions}
            value={bHostelId}
            onChange={setBHostelId}
            required
          />
          <NumberInput
            label="User ID"
            description="Numeric user ID from Institute IAM"
            min={1}
            value={bUserId}
            onChange={setBUserId}
            required
          />
          <Select
            label="Designated Role"
            data={[
              { value: "caretaker", label: "Hostel Caretaker" },
              { value: "warden", label: "Hostel Warden" },
            ]}
            value={bRole}
            onChange={setBRole}
            required
          />
          <TextInput
            label="Notes / Office Order #"
            placeholder="Office order reference..."
            value={bNotes}
            onChange={(e) => setBNotes(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setBindingModalOpen(false)}>Cancel</Button>
            <Button loading={createBinding.isPending} onClick={handleCreateBinding}>Assign Role</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Add Room */}
      <Modal opened={roomModalOpen} onClose={() => setRoomModalOpen(false)} title="Add Room to Hostel">
        <Stack gap="sm">
          <Select
            label="Hostel"
            placeholder="Select hostel"
            data={hostelOptions}
            value={rHostelId}
            onChange={setRHostelId}
            required
          />
          <TextInput
            label="Room Number"
            placeholder="e.g. A-101"
            value={rNumber}
            onChange={(e) => setRNumber(e.target.value)}
            required
          />
          <Group grow>
            <NumberInput label="Floor" min={0} value={rFloor} onChange={setRFloor} />
            <NumberInput label="Bed Capacity" min={1} max={10} value={rCap} onChange={setRCap} />
          </Group>
          <Select
            label="Room Type"
            data={[
              { value: "single", label: "Single" },
              { value: "double", label: "Double" },
              { value: "triple", label: "Triple" },
              { value: "guest", label: "Guest Room" },
            ]}
            value={rType}
            onChange={setRType}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setRoomModalOpen(false)}>Cancel</Button>
            <Button loading={createRoom.isPending} onClick={handleCreateRoom}>Save Room</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
