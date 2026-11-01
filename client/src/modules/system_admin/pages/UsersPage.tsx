import { useState } from "react";
import {
  ActionIcon,
  Button,
  Card,
  Grid,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Textarea,
  Tooltip,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
  FaBan,
  FaCheck,
  FaEdit,
  FaPlus,
  FaSearch,
  FaUserCheck,
  FaUsers,
} from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useBasicUsers,
  useCreateUser,
  useDeactivateUser,
  useReactivateUser,
  useUpdateUser,
} from "../api/hooks";
import type { BasicUser, UserType } from "../api/types";

export default function UsersPage() {
  const [filterType, setFilterType] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const { data: users = [], isLoading } = useBasicUsers({
    user_type: filterType || undefined,
    status: filterStatus || undefined,
    q: searchQuery || undefined,
  });

  const createUserMutation = useCreateUser();
  const updateUserMutation = useUpdateUser();
  const deactivateMutation = useDeactivateUser();
  const reactivateMutation = useReactivateUser();

  // Create User Modal state
  const [createOpened, { open: openCreate, close: closeCreate }] = useDisclosure(false);
  const [newType, setNewType] = useState<UserType>("student");
  const [newInstituteId, setNewInstituteId] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newFirstName, setNewFirstName] = useState("");
  const [newLastName, setNewLastName] = useState("");
  const [newContact, setNewContact] = useState("");
  const [newDept, setNewDept] = useState("Computer Science & Engineering");
  const [newProg, setNewProg] = useState("B.Tech");
  const [newDisc, setNewDisc] = useState("CSE");
  const [newBatch, setNewBatch] = useState<number | "">(2024);
  const [newEmpId, setNewEmpId] = useState("");

  // Edit Modal state
  const [editUser, setEditUser] = useState<BasicUser | null>(null);
  const [editFirstName, setEditFirstName] = useState("");
  const [editLastName, setEditLastName] = useState("");
  const [editContact, setEditContact] = useState("");
  const [editDept, setEditDept] = useState("");
  const [editReason, setEditReason] = useState("");

  // Deactivate / Reactivate Modal state
  const [actionUser, setActionUser] = useState<BasicUser | null>(null);
  const [actionType, setActionType] = useState<"deactivate" | "reactivate" | null>(null);
  const [actionReason, setActionReason] = useState("");

  const handleCreate = async () => {
    try {
      await createUserMutation.mutateAsync({
        user_type: newType,
        institute_id: newInstituteId,
        email: newEmail,
        first_name: newFirstName,
        last_name: newLastName,
        contact_number: newContact,
        department: newDept,
        programme: newType === "student" ? newProg : "",
        discipline: newType === "student" ? newDisc : "",
        batch_year: newType === "student" && typeof newBatch === "number" ? newBatch : undefined,
        employee_id: newType !== "student" ? newEmpId : "",
      });
      closeCreate();
      // reset
      setNewInstituteId("");
      setNewEmail("");
      setNewFirstName("");
      setNewLastName("");
      setNewContact("");
      setNewEmpId("");
    } catch {
      // Error handled by mutation
    }
  };

  const handleUpdate = async () => {
    if (!editUser) return;
    try {
      await updateUserMutation.mutateAsync({
        id: editUser.user_id,
        first_name: editFirstName,
        last_name: editLastName,
        contact_number: editContact,
        department: editDept,
        reason: editReason,
      });
      setEditUser(null);
    } catch {
      // Error handled
    }
  };

  const handleStatusAction = async () => {
    if (!actionUser || !actionType) return;
    try {
      if (actionType === "deactivate") {
        await deactivateMutation.mutateAsync({
          id: actionUser.user_id,
          reason: actionReason,
        });
      } else {
        await reactivateMutation.mutateAsync({
          id: actionUser.user_id,
          reason: actionReason,
        });
      }
      setActionUser(null);
      setActionType(null);
      setActionReason("");
    } catch {
      // Error handled
    }
  };

  return (
    <Stack gap="lg">
      <PageHeader
        title="User Identity Management"
        subtitle="Manage basic user identities across Student, Faculty, and Staff (CFR-SA-001..003)"
        action={
          <Button leftSection={<FaPlus />} onClick={openCreate} color="blue">
            Create User
          </Button>
        }
      />

      <Card withBorder p="md" radius="md">
        <Grid mb="md" align="flex-end">
          <Grid.Col span={{ base: 12, sm: 4 }}>
            <TextInput
              placeholder="Search by Institute ID, Name, Email..."
              leftSection={<FaSearch size={14} />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.currentTarget.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 6, sm: 4 }}>
            <Select
              placeholder="Filter by User Type"
              clearable
              data={[
                { value: "student", label: "Students" },
                { value: "faculty", label: "Faculty" },
                { value: "staff", label: "Staff" },
              ]}
              value={filterType}
              onChange={setFilterType}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 6, sm: 4 }}>
            <Select
              placeholder="Filter by Status"
              clearable
              data={[
                { value: "active", label: "Active" },
                { value: "deactivated", label: "Deactivated" },
                { value: "archived", label: "Archived" },
              ]}
              value={filterStatus}
              onChange={setFilterStatus}
            />
          </Grid.Col>
        </Grid>

        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Institute ID</Table.Th>
              <Table.Th>Name</Table.Th>
              <Table.Th>Email</Table.Th>
              <Table.Th>Type</Table.Th>
              <Table.Th>Department / Prog</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th style={{ textAlign: "right" }}>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {users.length === 0 ? (
              <Table.Tr>
                <Table.Td colSpan={7} style={{ textAlign: "center", padding: "40px 0" }}>
                  <Text c="dimmed">No user records match current filter criteria.</Text>
                </Table.Td>
              </Table.Tr>
            ) : (
              users.map((u) => (
                <Table.Tr key={u.user_id}>
                  <Table.Td>
                    <Text fw={600} size="sm">
                      {u.institute_id}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm">
                      {u.first_name} {u.last_name}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="sm" c="dimmed">
                      {u.email}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" tt="capitalize" fw={500}>
                      {u.user_type}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" c="dimmed">
                      {u.department || u.programme || "—"}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <StatusBadge status={u.status} />
                  </Table.Td>
                  <Table.Td style={{ textAlign: "right" }}>
                    <Group gap="xs" justify="flex-end">
                      <Tooltip label="Edit Profile">
                        <ActionIcon
                          variant="subtle"
                          color="blue"
                          onClick={() => {
                            setEditUser(u);
                            setEditFirstName(u.first_name);
                            setEditLastName(u.last_name);
                            setEditContact(u.contact_number || "");
                            setEditDept(u.department || "");
                            setEditReason("");
                          }}
                        >
                          <FaEdit size={14} />
                        </ActionIcon>
                      </Tooltip>

                      {u.status === "active" ? (
                        <Tooltip label="Deactivate Account">
                          <ActionIcon
                            variant="subtle"
                            color="orange"
                            onClick={() => {
                              setActionUser(u);
                              setActionType("deactivate");
                              setActionReason("");
                            }}
                          >
                            <FaBan size={14} />
                          </ActionIcon>
                        </Tooltip>
                      ) : u.status === "deactivated" ? (
                        <Tooltip label="Reactivate Account">
                          <ActionIcon
                            variant="subtle"
                            color="green"
                            onClick={() => {
                              setActionUser(u);
                              setActionType("reactivate");
                              setActionReason("");
                            }}
                          >
                            <FaUserCheck size={14} />
                          </ActionIcon>
                        </Tooltip>
                      ) : null}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))
            )}
          </Table.Tbody>
        </Table>
      </Card>

      {/* Create User Modal */}
      <Modal opened={createOpened} onClose={closeCreate} title="Create Basic User Account" size="lg">
        <Stack gap="sm">
          <Select
            label="User Type"
            required
            data={[
              { value: "student", label: "Student" },
              { value: "faculty", label: "Faculty" },
              { value: "staff", label: "Staff" },
            ]}
            value={newType}
            onChange={(val) => setNewType((val as UserType) || "student")}
          />

          <TextInput
            label="Institute ID"
            placeholder="e.g. 2024CS45 or FAC105"
            description="Immutable once established across Fusion (BR-SA-001)"
            required
            value={newInstituteId}
            onChange={(e) => setNewInstituteId(e.currentTarget.value)}
          />

          <TextInput
            label="Institute Email"
            placeholder="user@iiitdmj.ac.in"
            description="Must belong to iiitdmj.ac.in institutional domain (BR-SA-002)"
            required
            value={newEmail}
            onChange={(e) => setNewEmail(e.currentTarget.value)}
          />

          <Group grow>
            <TextInput
              label="First Name"
              required
              value={newFirstName}
              onChange={(e) => setNewFirstName(e.currentTarget.value)}
            />
            <TextInput
              label="Last Name"
              required
              value={newLastName}
              onChange={(e) => setNewLastName(e.currentTarget.value)}
            />
          </Group>

          <TextInput
            label="Contact Number"
            placeholder="+91 9876543210"
            value={newContact}
            onChange={(e) => setNewContact(e.currentTarget.value)}
          />

          <TextInput
            label="Department"
            required
            value={newDept}
            onChange={(e) => setNewDept(e.currentTarget.value)}
          />

          {newType === "student" ? (
            <>
              <Group grow>
                <Select
                  label="Programme"
                  data={["B.Tech", "M.Tech", "B.Des", "M.Des", "Ph.D"]}
                  value={newProg}
                  onChange={(v) => setNewProg(v || "B.Tech")}
                />
                <Select
                  label="Discipline"
                  data={["CSE", "ECE", "ME", "Design", "NS"]}
                  value={newDisc}
                  onChange={(v) => setNewDisc(v || "CSE")}
                />
              </Group>
              <NumberInput
                label="Batch Year"
                required
                value={newBatch}
                onChange={setNewBatch}
                min={2005}
                max={2035}
              />
            </>
          ) : (
            <TextInput
              label="Employee ID"
              placeholder="e.g. EMP404"
              required
              value={newEmpId}
              onChange={(e) => setNewEmpId(e.currentTarget.value)}
            />
          )}

          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={closeCreate}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              loading={createUserMutation.isPending}
              disabled={!newInstituteId || !newEmail || !newFirstName || !newLastName}
            >
              Establish Account
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Edit Profile Modal */}
      <Modal opened={!!editUser} onClose={() => setEditUser(null)} title="Update User Profile" size="md">
        {editUser && (
          <Stack gap="sm">
            <TextInput
              label="Institute ID"
              value={editUser.institute_id}
              disabled
              description="Institute ID is immutable (BR-SA-001)"
            />
            <TextInput label="User Type" value={editUser.user_type} disabled />

            <Group grow>
              <TextInput
                label="First Name"
                value={editFirstName}
                onChange={(e) => setEditFirstName(e.currentTarget.value)}
              />
              <TextInput
                label="Last Name"
                value={editLastName}
                onChange={(e) => setEditLastName(e.currentTarget.value)}
              />
            </Group>

            <TextInput
              label="Contact Number"
              value={editContact}
              onChange={(e) => setEditContact(e.currentTarget.value)}
            />

            <TextInput
              label="Department"
              value={editDept}
              onChange={(e) => setEditDept(e.currentTarget.value)}
            />

            <Textarea
              label="Reason for Modification"
              placeholder="Required for administrative audit trail"
              required
              value={editReason}
              onChange={(e) => setEditReason(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setEditUser(null)}>
                Cancel
              </Button>
              <Button onClick={handleUpdate} loading={updateUserMutation.isPending} disabled={!editReason}>
                Save Changes
              </Button>
            </Group>
          </Stack>
        )}
      </Modal>

      {/* Deactivate / Reactivate Modal */}
      <Modal
        opened={!!actionUser && !!actionType}
        onClose={() => {
          setActionUser(null);
          setActionType(null);
        }}
        title={`${actionType === "deactivate" ? "Deactivate" : "Reactivate"} User Account`}
      >
        <Stack gap="sm">
          <Text size="sm">
            Are you sure you want to {actionType} user{" "}
            <strong>
              {actionUser?.first_name} {actionUser?.last_name} ({actionUser?.institute_id})
            </strong>
            ?
          </Text>

          {actionType === "deactivate" && (
            <Text size="xs" c="orange">
              Deactivating a user automatically revokes/suspends their active roles (BR-SA-015).
            </Text>
          )}

          <Textarea
            label="Reason for Action"
            description="Mandatory for compliance logging and audit evidence"
            required
            value={actionReason}
            onChange={(e) => setActionReason(e.currentTarget.value)}
          />

          <Group justify="flex-end" mt="md">
            <Button
              variant="default"
              onClick={() => {
                setActionUser(null);
                setActionType(null);
              }}
            >
              Cancel
            </Button>
            <Button
              color={actionType === "deactivate" ? "red" : "green"}
              onClick={handleStatusAction}
              loading={deactivateMutation.isPending || reactivateMutation.isPending}
              disabled={!actionReason}
            >
              Confirm {actionType === "deactivate" ? "Deactivation" : "Reactivation"}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
