import { useState, useEffect } from "react";
import {
  Button,
  Text,
  Stack,
  Modal,
  rem,
  TextInput,
  MultiSelect,
  Container,
  Card,
  Grid,
  Group,
  Badge,
  Divider,
  ScrollArea,
  Paper,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import axiosInstance from "../../context/axiosInstance";
import { FaCheck, FaTimes } from 'react-icons/fa';
import PageHeader from "../../components/PageHeader/PageHeader";

const getErrorMessage = (err, fallback) => {
  if (!err.response) return "Could not reach the server. Please try again.";
  const { data } = err.response;
  return data?.error || data?.detail || fallback;
};

const EditUserRolePage = () => {
  const [username, setUsername] = useState("");
  const [userDetails, setUserDetails] = useState(null);
  const [roles, setRoles] = useState([]);
  const [currentRoles, setCurrentRoles] = useState([]);
  const [newRoles, setNewRoles] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const xIcon = <FaTimes style={{ width: rem(20), height: rem(20) }} />;
  const checkIcon = <FaCheck style={{ width: rem(20), height: rem(20) }} />;

  const fetchUserAndRoleDetails = async (target = username) => {
    try {
      setLoading(true);
      const response = await axiosInstance.get(
        `/get-user-roles-by-username/?username=${target}`
      );
      setUserDetails(response.data.user);
      setCurrentRoles(response.data.roles);
      setLoading(false);
    } catch (err) {
      setLoading(false);
      notifications.show({
        title: "Error",
        icon: xIcon,
        position: "top-center",
        withCloseButton: true,
        message: getErrorMessage(
          err,
          "Could not fetch user details. Please check the username."
        ),
        color: "red",
      });
    }
  };

  const handleSubmit = async () => {
    const target = userDetails.username;
    try {
      const updatedRoles = [...currentRoles, ...newRoles].filter(
        (role, index, self) => self.indexOf(role) === index
      );
      console.log(updatedRoles);

      await axiosInstance.put(`/update-user-roles/`, {
        username: target,
        roles: updatedRoles,
      });

      notifications.show({
        title: "Success",
        position: "top-center",
        icon: checkIcon,
        withCloseButton: true,
        message: "User roles updated successfully.",
        color: "green",
      });
      setCurrentRoles(updatedRoles);
      fetchUserAndRoleDetails(target);
      setNewRoles([]);
      setIsOpen(false);
    } catch (err) {
      notifications.show({
        title: "Error",
        position: "top-center",
        icon: xIcon,
        withCloseButton: true,
        message: getErrorMessage(err, "Could not update user roles."),
        color: "red",
      });
    }
  };

  const handleRemoveRole = (role) => {
    setCurrentRoles((prevRoles) => prevRoles.filter((r) => r !== role));
  };

  const fetchAvailableRoles = async () => {
    try {
      const response = await axiosInstance.get(`/view-roles/`);
      setRoles(response.data);
    } catch (error) {
      console.log(error.response);
    }
  };

  useEffect(() => {
    fetchAvailableRoles();
  }, []);

  return (
    <Container size="lg">
      <PageHeader
        title="Edit User's Role"
        subtitle="Look up a user and manage the roles assigned to their account."
      />

      <Grid gutter="lg">
        {/* User lookup and details */}
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card padding="lg" withBorder radius="lg">
            <Stack gap="md">
              <TextInput
                label="Username"
                placeholder="Enter username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") fetchUserAndRoleDetails();
                }}
                required
                size="md"
              />
              <Button onClick={() => fetchUserAndRoleDetails()}>Fetch User Details</Button>
            </Stack>

            {userDetails && (
              <>
                <Divider my="lg" />

                <Group justify="space-between" mb="sm">
                  <Text fw={600} size="lg">
                    User Details
                  </Text>
                  <Badge
                    size="lg"
                    variant="light"
                    color={userDetails.is_active ? "green" : "red"}
                  >
                    {userDetails.is_active ? "Active" : "Non-Active"}
                  </Badge>
                </Group>

                <Stack gap="xs">
                  <Text>
                    <Text span fw={600}>Name: </Text>
                    {userDetails.first_name}
                  </Text>
                  <Text>
                    <Text span fw={600}>Roll No: </Text>
                    {userDetails.username}
                  </Text>
                  <Text>
                    <Text span fw={600}>Date Joined: </Text>
                    {new Date(userDetails.date_joined).toLocaleDateString(undefined, {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </Text>
                </Stack>
              </>
            )}
          </Card>
        </Grid.Col>

        {/* Current roles and new role selection */}
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card padding="lg" withBorder radius="lg">
            {loading ? (
              <Text c="dimmed">Loading roles...</Text>
            ) : userDetails ? (
              <Stack gap="md">
                <Text fw={600} size="lg">
                  Current Roles
                </Text>

                <ScrollArea.Autosize mah={220}>
                  <Stack gap="xs">
                    {currentRoles.map((role) => (
                      <Paper key={role.name} withBorder radius="md" p="xs">
                        <Group justify="space-between" wrap="nowrap">
                          <Text fw={500}>
                            {role.name}{role.basic ? "(Base)" : ""}
                          </Text>
                          <Button
                            variant="outline"
                            color="red"
                            size="xs"
                            disabled={role.basic}
                            onClick={() => handleRemoveRole(role)}
                          >
                            Remove
                          </Button>
                        </Group>
                      </Paper>
                    ))}
                  </Stack>
                </ScrollArea.Autosize>

                <MultiSelect
                  label="Add new role"
                  placeholder="Select roles"
                  data={roles.map((role) => ({
                    value: role.name,
                    label: `${role.name}${role.basic ? "(Base)" : ""}`,
                  }))}
                  value={newRoles}
                  onChange={setNewRoles}
                  searchable
                  clearable
                  size="md"
                />

                <Button onClick={() => setIsOpen(true)} fullWidth>
                  Confirm Changes
                </Button>
              </Stack>
            ) : (
              <Text c="dimmed">No user details found</Text>
            )}
          </Card>
        </Grid.Col>
      </Grid>

      {/* Confirmation Modal */}
      <Modal
        opened={isOpen}
        onClose={() => setIsOpen(false)}
        title="Confirm Changes"
      >
        <Text>Are you sure you want to update the user roles?</Text>
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

export default EditUserRolePage;
