import {
  Alert,
  Badge,
  Button,
  Card,
  Container,
  Grid,
  Group,
  Loader,
  Modal,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import dayjs from "dayjs";
import { useState } from "react";
import { FaPlus, FaUserCog, FaUserShield } from "react-icons/fa";

import { useAssignCmsRole, useCmsRoles } from "../api/hooks";

export function RolesPage() {
  const [modalOpened, { open: openModal, close: closeModal }] = useDisclosure(false);
  const [roleType, setRoleType] = useState<"handler" | "supervisor">("handler");
  const [userId, setUserId] = useState("");
  const [startDate, setStartDate] = useState(dayjs().format("YYYY-MM-DDTHH:mm"));
  const [endDate, setEndDate] = useState(dayjs().add(1, "year").format("YYYY-MM-DDTHH:mm"));
  const [errorMsg, setErrorMsg] = useState("");

  const { data: roles, isLoading } = useCmsRoles();
  const assignRoleMutation = useAssignCmsRole();

  const handleAssignRole = async () => {
    if (!userId.trim()) {
      setErrorMsg("User ID is required.");
      return;
    }
    if (dayjs(endDate).isBefore(dayjs(startDate))) {
      setErrorMsg("End date must be after start date.");
      return;
    }
    setErrorMsg("");
    try {
      await assignRoleMutation.mutateAsync({
        role_type: roleType,
        user_id: Number(userId),
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
      });
      closeModal();
      setUserId("");
    } catch (err: any) {
      setErrorMsg(err?.response?.data?.detail || "Failed to assign CMS role.");
    }
  };

  return (
    <Container size="lg" py="lg">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <div>
            <Title order={2}>CMS Role Assignment</Title>
            <Text c="dimmed" size="sm">
              Time-bound assignment of institutional Complaint Handler and Supervisor roles
              (BR-CMS-035–038).
            </Text>
          </div>
          <Button leftSection={<FaPlus />} onClick={openModal}>
            Assign / Reassign Role
          </Button>
        </Group>

        <Alert color="blue" title="Single Active Holder Constraint">
          The system strictly enforces exactly one active role-holder per role type. Reassigning a
          role mid-cycle automatically deactivates the existing active assignment.
        </Alert>

        {isLoading ? (
          <Stack align="center" py="xl">
            <Loader size="md" />
          </Stack>
        ) : (
          <Grid>
            {/* Active Handler Card */}
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Card withBorder radius="md" p="lg">
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    <FaUserCog size={22} color="#1c7ed6" />
                    <Title order={4}>Complaint Handler</Title>
                  </Group>
                  <Badge color={roles?.active_handler ? "teal" : "gray"}>
                    {roles?.active_handler ? "ACTIVE" : "VACANT"}
                  </Badge>
                </Group>

                {roles?.active_handler ? (
                  <Stack gap="xs" mt="md">
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        User ID:
                      </Text>
                      <Text size="sm" fw={700}>
                        User #{roles.active_handler.user_id}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Valid From:
                      </Text>
                      <Text size="sm">
                        {dayjs(roles.active_handler.start_date).format("DD MMM YYYY, hh:mm A")}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Valid Until:
                      </Text>
                      <Text size="sm">
                        {dayjs(roles.active_handler.end_date).format("DD MMM YYYY, hh:mm A")}
                      </Text>
                    </Group>
                  </Stack>
                ) : (
                  <Text size="sm" c="dimmed" mt="md">
                    No active Complaint Handler assigned. Assign one to enable queue handling.
                  </Text>
                )}
              </Card>
            </Grid.Col>

            {/* Active Supervisor Card */}
            <Grid.Col span={{ base: 12, md: 6 }}>
              <Card withBorder radius="md" p="lg">
                <Group justify="space-between" mb="xs">
                  <Group gap="xs">
                    <FaUserShield size={22} color="#f59f00" />
                    <Title order={4}>Complaint Supervisor</Title>
                  </Group>
                  <Badge color={roles?.active_supervisor ? "teal" : "gray"}>
                    {roles?.active_supervisor ? "ACTIVE" : "VACANT"}
                  </Badge>
                </Group>

                {roles?.active_supervisor ? (
                  <Stack gap="xs" mt="md">
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        User ID:
                      </Text>
                      <Text size="sm" fw={700}>
                        User #{roles.active_supervisor.user_id}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Valid From:
                      </Text>
                      <Text size="sm">
                        {dayjs(roles.active_supervisor.start_date).format("DD MMM YYYY, hh:mm A")}
                      </Text>
                    </Group>
                    <Group justify="space-between">
                      <Text size="sm" c="dimmed">
                        Valid Until:
                      </Text>
                      <Text size="sm">
                        {dayjs(roles.active_supervisor.end_date).format("DD MMM YYYY, hh:mm A")}
                      </Text>
                    </Group>
                  </Stack>
                ) : (
                  <Text size="sm" c="dimmed" mt="md">
                    No active Complaint Supervisor assigned.
                  </Text>
                )}
              </Card>
            </Grid.Col>
          </Grid>
        )}

        {/* Modal: Assign Role */}
        <Modal opened={modalOpened} onClose={closeModal} title="Assign / Reassign CMS Role">
          <Stack gap="md">
            {errorMsg && (
              <Alert color="red" onClose={() => setErrorMsg("")} withCloseButton>
                {errorMsg}
              </Alert>
            )}

            <Select
              label="Role Type"
              required
              value={roleType}
              onChange={(val) => setRoleType((val as "handler" | "supervisor") || "handler")}
              data={[
                { value: "handler", label: "Complaint Handler" },
                { value: "supervisor", label: "Complaint Supervisor" },
              ]}
            />

            <TextInput
              label="User ID"
              placeholder="e.g. 102"
              required
              value={userId}
              onChange={(e) => setUserId(e.currentTarget.value)}
            />

            <TextInput
              label="Start Date / Time"
              type="datetime-local"
              required
              value={startDate}
              onChange={(e) => setStartDate(e.currentTarget.value)}
            />

            <TextInput
              label="End Date / Time"
              type="datetime-local"
              required
              value={endDate}
              onChange={(e) => setEndDate(e.currentTarget.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={closeModal}>
                Cancel
              </Button>
              <Button loading={assignRoleMutation.isPending} onClick={handleAssignRole}>
                Confirm Assignment
              </Button>
            </Group>
          </Stack>
        </Modal>
      </Stack>
    </Container>
  );
}

export default RolesPage;

