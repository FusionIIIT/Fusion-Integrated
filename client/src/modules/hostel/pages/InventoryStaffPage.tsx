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
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaBoxes, FaUserTie } from "react-icons/fa";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useCreateInventory,
  useCreateStaff,
  useHostels,
  useInventory,
  useStaff,
} from "../api/hooks";
import type { InventoryCategory, StaffRole, StaffShift } from "../api/types";

export default function InventoryStaffPage() {
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const hostelId = selectedHostel ? Number(selectedHostel) : undefined;

  const { data: hostelsData } = useHostels();
  const { data: inventoryData, error: inventoryError } = useInventory({ hostel_id: hostelId });
  const { data: staffData } = useStaff({ hostel_id: hostelId });

  const createInventory = useCreateInventory();
  const createStaff = useCreateStaff();

  const [invModalOpen, setInvModalOpen] = useState(false);
  const [staffModalOpen, setStaffModalOpen] = useState(false);

  // Inventory form state
  const [invHostelId, setInvHostelId] = useState<string | null>(null);
  const [itemName, setItemName] = useState("");
  const [category, setCategory] = useState<string>("furniture");
  const [quantityTotal, setQuantityTotal] = useState<number | string>(10);
  const [quantityInUse, setQuantityInUse] = useState<number | string>(5);
  const [locationOrRoom, setLocationOrRoom] = useState("");
  const [conditionNotes, setConditionNotes] = useState("");

  // Staff form state
  const [staffHostelId, setStaffHostelId] = useState<string | null>(null);
  const [staffName, setStaffName] = useState("");
  const [staffPhone, setStaffPhone] = useState("");
  const [staffRole, setStaffRole] = useState<string>("cleaner");
  const [staffShift, setStaffShift] = useState<string>("morning");

  const handleCreateInventory = async () => {
    if (!invHostelId) return;
    try {
      await createInventory.mutateAsync({
        hostel: Number(invHostelId),
        item_name: itemName,
        category: category as InventoryCategory,
        quantity_total: Number(quantityTotal),
        quantity_in_use: Number(quantityInUse),
        location_or_room: locationOrRoom,
        condition_notes: conditionNotes,
      });
      notifications.show({ title: "Success", message: "Inventory item recorded", color: "green" });
      setInvModalOpen(false);
      setItemName("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to record inventory", color: "red" });
    }
  };

  const handleCreateStaff = async () => {
    if (!staffHostelId) return;
    try {
      await createStaff.mutateAsync({
        hostel: Number(staffHostelId),
        name: staffName,
        phone: staffPhone,
        role: staffRole as StaffRole,
        shift: staffShift as StaffShift,
        is_active: true,
      });
      notifications.show({ title: "Success", message: "Staff member added", color: "green" });
      setStaffModalOpen(false);
      setStaffName("");
      setStaffPhone("");
    } catch (err: any) {
      notifications.show({ title: "Error", message: err.message || "Failed to add staff", color: "red" });
    }
  };

  if (inventoryError) return <Container size="xl"><ErrorState error={inventoryError} /></Container>;

  const hostels = hostelsData?.results ?? [];
  const inventory = inventoryData?.results ?? [];
  const staff = staffData?.results ?? [];

  return (
    <Container size="xl">
      <PageHeader
        title="Inventory & Staff"
        subtitle="Manage hostel furniture, consumables, electrical equipment, and housekeeping staff rosters"
        action={
          <Group>
            <Button variant="light" leftSection={<FaBoxes size={14} />} onClick={() => setInvModalOpen(true)}>
              Add Inventory
            </Button>
            <Button leftSection={<FaUserTie size={14} />} onClick={() => setStaffModalOpen(true)}>
              Register Staff
            </Button>
          </Group>
        }
      />

      <Group mb="md">
        <Select
          placeholder="Filter by hostel"
          clearable
          data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
          value={selectedHostel}
          onChange={setSelectedHostel}
          style={{ width: 280 }}
        />
      </Group>

      <Tabs defaultValue="inventory" keepMounted={false}>
        <Tabs.List mb="md">
          <Tabs.Tab value="inventory" leftSection={<FaBoxes size={14} />}>
            Operational Inventory ({inventory.length})
          </Tabs.Tab>
          <Tabs.Tab value="staff" leftSection={<FaUserTie size={14} />}>
            Hostel Staff Roster ({staff.length})
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="inventory">
          <Card withBorder radius="md">
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Item Name</Table.Th>
                  <Table.Th>Hostel</Table.Th>
                  <Table.Th>Category</Table.Th>
                  <Table.Th>Stock (Total / In Use / Avail)</Table.Th>
                  <Table.Th>Location / Room</Table.Th>
                  <Table.Th>Condition Notes</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {inventory.map((item) => (
                  <Table.Tr key={item.id}>
                    <Table.Td fw={600}>{item.item_name}</Table.Td>
                    <Table.Td>{item.hostel_name || `Hostel #${item.hostel}`}</Table.Td>
                    <Table.Td>
                      <Badge variant="outline">{item.category.toUpperCase()}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Text size="sm">{item.quantity_total} total ({item.quantity_in_use} in use, {item.quantity_available} avail)</Text>
                    </Table.Td>
                    <Table.Td>{item.location_or_room || "General Store"}</Table.Td>
                    <Table.Td>{item.condition_notes || "Good"}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="staff">
          <Card withBorder radius="md">
            <Table highlightOnHover verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Staff Name</Table.Th>
                  <Table.Th>Hostel</Table.Th>
                  <Table.Th>Role / Trade</Table.Th>
                  <Table.Th>Shift</Table.Th>
                  <Table.Th>Phone</Table.Th>
                  <Table.Th>Status</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {staff.map((s) => (
                  <Table.Tr key={s.id}>
                    <Table.Td fw={600}>{s.name}</Table.Td>
                    <Table.Td>{s.hostel_name || `Hostel #${s.hostel}`}</Table.Td>
                    <Table.Td>
                      <Badge color="blue">{s.role.toUpperCase()}</Badge>
                    </Table.Td>
                    <Table.Td>
                      <Badge variant="dot" color={s.shift === "night" ? "indigo" : "orange"}>
                        {s.shift.toUpperCase()}
                      </Badge>
                    </Table.Td>
                    <Table.Td>{s.phone}</Table.Td>
                    <Table.Td>
                      <Badge color={s.is_active ? "green" : "gray"}>
                        {s.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Modal: Add Inventory */}
      <Modal opened={invModalOpen} onClose={() => setInvModalOpen(false)} title="Record Inventory Asset" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={invHostelId}
            onChange={setInvHostelId}
          />
          <TextInput label="Item / Asset Name" placeholder="e.g. Study Tables, Ceiling Fans, Water Coolers" required value={itemName} onChange={(e) => setItemName(e.target.value)} />
          <Select
            label="Category"
            required
            data={[
              { value: "furniture", label: "Furniture (Beds, Tables, Chairs)" },
              { value: "electrical", label: "Electrical (Fans, Lights, Geysers)" },
              { value: "cleaning", label: "Cleaning Supplies & Equipment" },
              { value: "bedding", label: "Bedding & Mattresses" },
              { value: "appliance", label: "Appliances (Water Coolers, Washing Machines)" },
              { value: "sports", label: "Sports & Recreation" },
              { value: "other", label: "Other" },
            ]}
            value={category}
            onChange={(val) => val && setCategory(val)}
          />
          <Group grow>
            <NumberInput label="Total Quantity" min={1} required value={quantityTotal} onChange={setQuantityTotal} />
            <NumberInput label="In-Use Quantity" min={0} required value={quantityInUse} onChange={setQuantityInUse} />
          </Group>
          <TextInput label="Storage Location / Block / Room" placeholder="e.g. Ground Floor Store, Wing B" value={locationOrRoom} onChange={(e) => setLocationOrRoom(e.target.value)} />
          <TextInput label="Condition Notes" placeholder="e.g. New consignment, serviced" value={conditionNotes} onChange={(e) => setConditionNotes(e.target.value)} />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setInvModalOpen(false)}>Cancel</Button>
            <Button loading={createInventory.isPending} onClick={handleCreateInventory}>Save Asset</Button>
          </Group>
        </Stack>
      </Modal>

      {/* Modal: Register Staff */}
      <Modal opened={staffModalOpen} onClose={() => setStaffModalOpen(false)} title="Register Hostel Staff" centered>
        <Stack gap="sm">
          <Select
            label="Hostel"
            required
            data={hostels.map((h) => ({ value: String(h.id), label: `${h.name} (${h.code})` }))}
            value={staffHostelId}
            onChange={setStaffHostelId}
          />
          <TextInput label="Staff Full Name" required value={staffName} onChange={(e) => setStaffName(e.target.value)} />
          <TextInput label="Mobile Phone" placeholder="10-digit mobile" required value={staffPhone} onChange={(e) => setStaffPhone(e.target.value)} />
          <Select
            label="Role Trade"
            required
            data={[
              { value: "cleaner", label: "Cleaner / Housekeeping" },
              { value: "electrician", label: "Electrician" },
              { value: "plumber", label: "Plumber" },
              { value: "security", label: "Security Guard" },
              { value: "mess_helper", label: "Mess Helper" },
              { value: "attendant", label: "Hostel Attendant" },
            ]}
            value={staffRole}
            onChange={(val) => val && setStaffRole(val)}
          />
          <Select
            label="Assigned Shift"
            required
            data={[
              { value: "morning", label: "Morning (6 AM - 2 PM)" },
              { value: "evening", label: "Evening (2 PM - 10 PM)" },
              { value: "night", label: "Night (10 PM - 6 AM)" },
            ]}
            value={staffShift}
            onChange={(val) => val && setStaffShift(val)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setStaffModalOpen(false)}>Cancel</Button>
            <Button loading={createStaff.isPending} onClick={handleCreateStaff}>Register Staff</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
