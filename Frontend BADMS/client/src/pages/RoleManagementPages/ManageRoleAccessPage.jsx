import { useState, useEffect } from "react";
import {
  Button,
  Text,
  Stack,
  Modal,
  Select,
  Group,
  rem,
  Container,
  Checkbox,
  Loader,
  Card,
  SimpleGrid,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import axiosInstance from "../../context/axiosInstance";
import { FaCheck, FaTimes } from 'react-icons/fa';
import PageHeader from "../../components/PageHeader/PageHeader";

const ManageRoleAccessPage = () => {

  const [roleName, setRoleName] = useState("");
  const [roles, setRoles] = useState([]);
  const [moduleAccess, setModuleAccess] = useState(null);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  const xIcon = <FaTimes style={{ width: rem(20), height: rem(20) }} />;
  const checkIcon = <FaCheck style={{ width: rem(20), height: rem(20) }} />;

  useEffect(() => {
    const fetchRoles = async () => {
      try {
        const response = await axiosInstance.get(`/view-roles/`);
        setRoles(response.data.map((role) => ({
          label: role.name,
          value: role.name,
        })));
      } catch (error) {
        notifications.show({
          title: "Error",
          position: "top-center",
          icon: xIcon,
          withCloseButton: true,
          message: "Could not fetch roles.",
          color: "red",
        });
        console.log("Error fetching roles: ", error);
      }
    }
    fetchRoles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchModuleAccess = async () => {
    setLoading(true);

    try {
      const response = await axiosInstance.get(`/get-module-access/`, {
        params: { designation: roleName },
      });
      setModuleAccess(response.data);
    } catch (error) {
      notifications.show({
        title: "Error",
        position: "top-center",
        icon: xIcon,
        withCloseButton: true,
        message: `Failed to fetch module access for ${roleName}`,
        color: "red",
      });
      console.error("Error fetching module access: ", error);
    } finally {
      setLoading(false);
    };
  };

  const handleModuleChange = (moduleName) => {
    setModuleAccess((prevState) => ({
      ...prevState,
      [moduleName]: !prevState[moduleName],
    }));
  };

  useEffect(() => {
    console.log(moduleAccess);
  }, [moduleAccess]);

  const handleSubmit = async () => {
    setIsOpen(false);
    try {
      await axiosInstance.put(`/modify-roleaccess/`, {
        designation: roleName,
        ...moduleAccess,
      });

      notifications.show({
        title: "Success",
        position: "top-center",
        icon: checkIcon,
        withCloseButton: true,
        message: "Role access updated successfully.",
        color: "green",
      });
    } catch (error) {
      notifications.show({
        title: "Error",
        position: "top-center",
        icon: xIcon,
        withCloseButton: true,
        message: `Failed to update role access for ${roleName}`,
        color: "red",
      });
      console.error("Error updating role access: ", error);
    };
  };

  return (
    <Container size="xl">
      <PageHeader
        title="Manage Role Access"
        subtitle="Control which modules each role can access across the system."
      />

      {/* Role selection */}
      <Card padding="lg" withBorder radius="lg" mb="lg">
        <Stack gap="md">
          <Select
            label="Select Role"
            placeholder="Choose a role"
            searchable
            data={roles}
            value={roleName}
            onChange={setRoleName}
            required
            size="md"
          />

          <Group justify="flex-start">
            <Button onClick={fetchModuleAccess}>
              Fetch module access information
            </Button>
          </Group>
        </Stack>
      </Card>

      {loading && (
        <Group justify="center" my="xl">
          <Loader size="lg" />
        </Group>
      )}

      {/* Module access grid */}
      {moduleAccess && (
        <Card padding="lg" withBorder radius="lg">
          <Text fw={600} size="lg" mb="md">
            Manage module access for {roleName}
          </Text>

          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
            {Object.keys(moduleAccess).filter((module) => module !== "designation" && module !== "id").map((module) => (
              <Checkbox
                key={module}
                label={module.replace(/_/g, " ").toUpperCase()}
                checked={moduleAccess[module]}
                onChange={() => handleModuleChange(module)}
              />
            ))}
          </SimpleGrid>

          <Group justify="flex-end" mt="xl">
            <Button onClick={() => setIsOpen(true)}>
              Confirm changes
            </Button>
          </Group>
        </Card>
      )}

      {/* Confirmation Modal */}
      <Modal
        opened={isOpen}
        onClose={() => setIsOpen(false)}
        title="Confirm changes"
      >
        <Text>Are you sure you want to update the role access for {roleName} ?</Text>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={() => setIsOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit}>
            Confirm
          </Button>
        </Group>
      </Modal>
    </Container>
  );
};

export default ManageRoleAccessPage;
