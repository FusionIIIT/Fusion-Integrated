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
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { FaBoxes, FaUserTie, FaHistory } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import {
  useCreateInventoryItem,
  useCreateStaffAssignment,
  useHostels,
  useInventory,
  useInventoryAudits,
  useStaffAssignments,
} from "../api/hooks";
import type { HostelInventoryItem, StaffAssignment } from "../api/types";

export default function InventoryStaffPage() {
  const { data: hostels } = useHostels();
  const [selectedHostel, setSelectedHostel] = useState<string | null>(null);
  const [mainTab, setMainTab] = useState<string | null>("inventory");

  // Inventory queries & mutations
  const {
    data: items,
    isPending: itemsPending,
    error: itemsError,
  } = useInventory({
    hostel_id: selectedHostel ? Number(selectedHostel) : undefined,
  });

  const createItemMutation = useCreateInventoryItem();

  // Staff queries & mutations
  const {
    data: staffList,
    isPending: staffPending,
    error: staffError,
  } = useStaffAssignments(selectedHostel ? Number(selectedHostel) : undefined);

  const createStaffMutation = useCreateStaffAssignment();

  // Inventory Modal
  const [itemModalOpen, setItemModalOpen] = useState(false);
  const [iHostelId, setIHostelId] = useState<string | null>(null);
  const [iName, setIName] = useState("");
  const [iCategory, setICategory] = useState<string | null>("furniture");
  const [iTotal, setITotal] = useState<number | string>(10);
  const [iInUse, setIInUse] = useState<number | string>(0);
  const [iAvailable, setIAvailable] = useState<number | string>(10);
  const [iCondition, setICondition] = useState<string | null>("good");
  const [iLocation, setILocation] = useState("Store Room");

  // Audit modal
  const [auditModalOpen, setAuditModalOpen] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<number | undefined>(undefined);
  const { data: auditLogs, isPending: auditPending } = useInventoryAudits(selectedItemId);

  // Staff Modal
  const [staffModalOpen, setStaffModalOpen] = useState(false);
  const [sHostelId, setSHostelId] = useState<string | null>(null);
  const [sName, setSName] = useState("");
  const [sRole, setSRole] = useState("Cleaning Staff");
  const [sShift, setSShift] = useState<string | null>("morning");
  const [sContact, setSContact] = useState("");
  const [sLocation, setSLocation] = useState("Block A / Common Areas");

  if (itemsError || staffError) {
    return (
      <Container size="xl">
        <ErrorState error={itemsError || staffError} />
      </Container>
    );
  }

  const handleSaveItem = async () => {
    if (!iHostelId || !iName) return;
    await createItemMutation.mutateAsync({
      hostel: Number(iHostelId),
      item_name: iName,
      category: iCategory || "other",
      total_quantity: Number(iTotal),
      in_use_quantity: Number(iInUse),
      available_quantity: Number(iAvailable),
      condition: iCondition || "good",
      location: iLocation,
    });
    setItemModalOpen(false);
    setIName("");
  };

  const handleSaveStaff = async () => {
    if (!sHostelId || !sName) return;
    await createStaffMutation.mutateAsync({
      hostel: Number(sHostelId),
      staff_name: sName,
      role_designation: sRole,
      shift: sShift || "morning",
      contact_number: sContact,
      duty_location: sLocation,
      is_active: true,
    });
    setStaffModalOpen(false);
    setSName("");
    setSContact("");
  };

  return (
    <Container size="xl">
      <Stack gap="lg">
        <PageHeader
          title="Hostel Inventory & Staff Management"
          subtitle="Track furniture, assets, consumables, audit logs, and caretaker staff duty rosters"
          action={
            <Group>
              <Button
                variant="outline"
                leftSection={<FaBoxes />}
                onClick={() => {
                  if (hostels && hostels.length > 0 && hostels[0]) setIHostelId(String(hostels[0].id));
                  setItemModalOpen(true);
                }}
              >
                Add Inventory Item
              </Button>
              <Button
                leftSection={<FaUserTie />}
                onClick={() => {
                  if (hostels && hostels.length > 0 && hostels[0]) setSHostelId(String(hostels[0].id));
                  setStaffModalOpen(true);
                }}
              >
                Assign Staff Member
              </Button>
            </Group>
          }
        />

        <Card withBorder radius="md">
          <Group justify="space-between" mb="md">
            <Select
              placeholder="Filter by hostel"
              clearable
              value={selectedHostel}
              onChange={setSelectedHostel}
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              style={{ width: 280 }}
            />

            <Tabs value={mainTab} onChange={setMainTab}>
              <Tabs.List>
                <Tabs.Tab value="inventory" leftSection={<FaBoxes />}>
                  Inventory Items ({items?.length || 0})
                </Tabs.Tab>
                <Tabs.Tab value="staff" leftSection={<FaUserTie />}>
                  Staff Shift Roster ({staffList?.length || 0})
                </Tabs.Tab>
              </Tabs.List>
            </Tabs>
          </Group>

          {mainTab === "inventory" ? (
            <DataTable<HostelInventoryItem>
              rows={items || []}
              loading={itemsPending}
              rowKey={(r) => r.id}
              columns={[
                {
                  key: "id",
                  header: "ID",
                  render: (r) => <Text size="sm" fw={600}>#{r.id}</Text>,
                },
                {
                  key: "item",
                  header: "Item & Hostel",
                  render: (r) => (
                    <Stack gap={2}>
                      <Text size="sm" fw={600}>{r.item_name}</Text>
                      <Text size="xs" c="dimmed">{r.hostel_name}</Text>
                    </Stack>
                  ),
                },
                {
                  key: "category",
                  header: "Category",
                  render: (r) => (
                    <Badge variant="outline" size="sm">
                      {r.category.toUpperCase()}
                    </Badge>
                  ),
                },
                {
                  key: "quantities",
                  header: "Quantities (Total / In-Use / Avail)",
                  render: (r) => (
                    <Group gap="xs">
                      <Badge color="blue" size="sm">Total: {r.total_quantity}</Badge>
                      <Badge color="orange" size="sm">In-Use: {r.in_use_quantity}</Badge>
                      <Badge color="teal" size="sm">Free: {r.available_quantity}</Badge>
                    </Group>
                  ),
                },
                {
                  key: "condition",
                  header: "Condition",
                  render: (r) => {
                    const color =
                      r.condition === "good" ? "teal" : r.condition === "fair" ? "yellow" : "red";
                    return <Badge color={color}>{r.condition.replace("_", " ")}</Badge>;
                  },
                },
                {
                  key: "location",
                  header: "Location / Storage",
                  render: (r) => <Text size="xs">{r.location || "Store Room"}</Text>,
                },
                {
                  key: "actions",
                  header: "Audit Trail",
                  render: (r) => (
                    <Button
                      size="xs"
                      variant="light"
                      leftSection={<FaHistory />}
                      onClick={() => {
                        setSelectedItemId(r.id);
                        setAuditModalOpen(true);
                      }}
                    >
                      Logs
                    </Button>
                  ),
                },
              ]}
              empty={{
                title: "No Inventory Items",
                description: "No inventory records found for this hostel.",
              }}
            />
          ) : (
            <DataTable<StaffAssignment>
              rows={staffList || []}
              loading={staffPending}
              rowKey={(r) => r.id}
              columns={[
                {
                  key: "id",
                  header: "ID",
                  render: (r) => <Text size="sm" fw={600}>#{r.id}</Text>,
                },
                {
                  key: "staff_name",
                  header: "Staff Member",
                  render: (r) => (
                    <Stack gap={2}>
                      <Text size="sm" fw={600}>{r.staff_name}</Text>
                      <Text size="xs" c="dimmed">{r.contact_number || "No contact"}</Text>
                    </Stack>
                  ),
                },
                {
                  key: "hostel_name",
                  header: "Hostel",
                  render: (r) => <Text size="sm">{r.hostel_name}</Text>,
                },
                {
                  key: "role_designation",
                  header: "Designation",
                  render: (r) => (
                    <Badge variant="outline">{r.role_designation}</Badge>
                  ),
                },
                {
                  key: "shift",
                  header: "Shift",
                  render: (r) => {
                    const colors: Record<string, string> = {
                      morning: "orange",
                      evening: "blue",
                      night: "indigo",
                      general: "gray",
                    };
                    return <Badge color={colors[r.shift] || "gray"}>{r.shift.toUpperCase()}</Badge>;
                  },
                },
                {
                  key: "duty_location",
                  header: "Duty Post / Floor",
                  render: (r) => <Text size="xs">{r.duty_location}</Text>,
                },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => (
                    <Badge color={r.is_active ? "teal" : "gray"}>
                      {r.is_active ? "Active" : "Inactive"}
                    </Badge>
                  ),
                },
              ]}
              empty={{
                title: "No Staff Assignments",
                description: "No staff roster entries found for this hostel.",
              }}
            />
          )}
        </Card>

        {/* Modal: Add Inventory Item */}
        <Modal
          opened={itemModalOpen}
          onClose={() => setItemModalOpen(false)}
          title="Register Hostel Inventory Item"
          size="md"
        >
          <Stack gap="sm">
            <Select
              label="Hostel"
              required
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              value={iHostelId}
              onChange={setIHostelId}
            />

            <TextInput
              label="Item Name"
              required
              placeholder="e.g. Study Table, Ceiling Fan, Mattress"
              value={iName}
              onChange={(e) => setIName(e.target.value)}
            />

            <Select
              label="Category"
              data={[
                { value: "furniture", label: "Furniture (Beds, Tables, Chairs)" },
                { value: "electrical", label: "Electrical (Fans, Lights, ACs)" },
                { value: "cleaning", label: "Sanitary / Cleaning Assets" },
                { value: "sports", label: "Sports & Recreation Equipments" },
                { value: "linen", label: "Linen & Bedding" },
                { value: "other", label: "Other Equipment" },
              ]}
              value={iCategory}
              onChange={setICategory}
            />

            <Group grow>
              <NumberInput
                label="Total Quantity"
                min={0}
                value={iTotal}
                onChange={setITotal}
              />
              <NumberInput
                label="In-Use"
                min={0}
                value={iInUse}
                onChange={setIInUse}
              />
              <NumberInput
                label="Available"
                min={0}
                value={iAvailable}
                onChange={setIAvailable}
              />
            </Group>

            <Group grow>
              <Select
                label="Condition"
                data={[
                  { value: "good", label: "Good" },
                  { value: "fair", label: "Fair" },
                  { value: "needs_repair", label: "Needs Repair" },
                ]}
                value={iCondition}
                onChange={setICondition}
              />
              <TextInput
                label="Storage Location"
                value={iLocation}
                onChange={(e) => setILocation(e.target.value)}
              />
            </Group>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setItemModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={createItemMutation.isPending}
                disabled={!iHostelId || !iName}
                onClick={handleSaveItem}
              >
                Save Item
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: View Audit Log */}
        <Modal
          opened={auditModalOpen}
          onClose={() => setAuditModalOpen(false)}
          title={`Inventory Audit Log (Item #${selectedItemId})`}
          size="lg"
        >
          <Stack gap="sm">
            {auditPending ? (
              <Text size="sm">Loading audit records...</Text>
            ) : !auditLogs || auditLogs.length === 0 ? (
              <Text size="sm" c="dimmed">No changes logged for this item yet.</Text>
            ) : (
              auditLogs.map((log) => (
                <Card key={log.id} withBorder p="xs">
                  <Group justify="space-between">
                    <Badge variant="outline">{log.action}</Badge>
                    <Text size="xs" c="dimmed">{new Date(log.timestamp).toLocaleString()}</Text>
                  </Group>
                  <Text size="sm" mt={4}>{log.details}</Text>
                  <Text size="xs" c="dimmed">Performed by User #{log.performed_by_user_id}</Text>
                </Card>
              ))
            )}
            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setAuditModalOpen(false)}>
                Close
              </Button>
            </Group>
          </Stack>
        </Modal>

        {/* Modal: Assign Staff */}
        <Modal
          opened={staffModalOpen}
          onClose={() => setStaffModalOpen(false)}
          title="Assign Hostel Staff Member"
          size="md"
        >
          <Stack gap="sm">
            <Select
              label="Hostel"
              required
              data={(hostels || []).map((h) => ({
                value: String(h.id),
                label: `${h.name} (${h.code})`,
              }))}
              value={sHostelId}
              onChange={setSHostelId}
            />

            <TextInput
              label="Staff Member Full Name"
              required
              placeholder="e.g. Ramesh Kumar"
              value={sName}
              onChange={(e) => setSName(e.target.value)}
            />

            <Group grow>
              <TextInput
                label="Role / Designation"
                value={sRole}
                onChange={(e) => setSRole(e.target.value)}
              />
              <Select
                label="Shift"
                data={[
                  { value: "morning", label: "Morning (06:00 - 14:00)" },
                  { value: "evening", label: "Evening (14:00 - 22:00)" },
                  { value: "night", label: "Night (22:00 - 06:00)" },
                  { value: "general", label: "General Day Shift" },
                ]}
                value={sShift}
                onChange={setSShift}
              />
            </Group>

            <Group grow>
              <TextInput
                label="Contact Number"
                placeholder="10-digit mobile"
                value={sContact}
                onChange={(e) => setSContact(e.target.value)}
              />
              <TextInput
                label="Duty Area / Location"
                value={sLocation}
                onChange={(e) => setSLocation(e.target.value)}
              />
            </Group>

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setStaffModalOpen(false)}>
                Cancel
              </Button>
              <Button
                loading={createStaffMutation.isPending}
                disabled={!sHostelId || !sName}
                onClick={handleSaveStaff}
              >
                Assign Staff
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}
