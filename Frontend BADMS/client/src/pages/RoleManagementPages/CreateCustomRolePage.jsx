import { useState, useRef, useEffect } from "react";
import {
  Button,
  Text,
  Stack,
  Modal,
  Group,
  Container,
  Card,
  TextInput,
  Progress,
  rem,
  Select,
} from "@mantine/core";
import { FaCheck, FaTimes } from 'react-icons/fa';
import { notifications } from '@mantine/notifications';
import { createCustomRole } from "../../api/Roles";
import PageHeader from "../../components/PageHeader/PageHeader";

function getProgress(inputs) {
  const filledInputs = inputs.filter((input) => input.length > 0);
  return (filledInputs.length / inputs.length) * 100;
}

const CreateCustomRolePage = () => {
  const xIcon = <FaTimes style={{ width: rem(20), height: rem(20) }} />;
  const checkIcon = <FaCheck style={{ width: rem(20), height: rem(20) }} />;

  const [roleDetails, setRoleDetails] = useState({
    name: "",
    full_name: "",
    type: "",
    basic: false,
  });

  const progress = getProgress([roleDetails.name, roleDetails.full_name, roleDetails.type]);
  const [isOpen, setIsOpen] = useState(false);
  const [validationModalOpen, setValidationModalOpen] = useState(false);
  const submitButtonRef = useRef(null);
  const confirmButtonRef = useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!roleDetails.name || !roleDetails.full_name || !roleDetails.type) {
      setValidationModalOpen(true);
      return;
    }

    try {
      await createCustomRole(roleDetails);
      // await axios.post(
      //   "http://127.0.0.1:8000/api/create-role/",
      //   roleDetails,
      //   {
      //     headers: {
      //       "Content-Type": "application/json",
      //     },
      //   }
      // );

      notifications.show({
        icon: checkIcon,
        title: "Success",
        position: "top-center",
        withCloseButton: true,
        autoClose: 5000,
        message: "Role created successfully.",
        color: "green",
      });

      setRoleDetails({
        name: "",
        full_name: "",
        type: "",
        basic: false,
      });

      setIsOpen(false);

    } catch (err) {
      const errorMessage = err.response
        ? `Error: ${JSON.stringify(err.response.data)}`
        : err.request
          ? "No response received from the server"
          : `Error: ${err.message}`;

      notifications.show({
        icon: xIcon,
        title: "Error",
        position: "top-center",
        withCloseButton: true,
        autoClose: 5000,
        message: errorMessage,
        color: "red",
      });
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setRoleDetails((prevRoleDetails) => ({
      ...prevRoleDetails,
      [name]: value,
    }));
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      if (isOpen) {
        confirmButtonRef.current.click();
      } else {
        submitButtonRef.current.click();
      }
    }
  };

  useEffect(() => {
    document.addEventListener("keydown", handleKeyPress);
    return () => {
      document.removeEventListener("keydown", handleKeyPress);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  return (
    <Container size="lg">
      <PageHeader
        title="Create Custom Role"
        subtitle="Define a new designation and its type for the institute."
      />

      <Card padding="lg" withBorder radius="lg" maw={640} mx="auto">
        <Progress
          value={progress}
          size="sm"
          radius="xl"
          color={progress < 50 ? "red" : progress < 75 ? "orange" : "teal"}
        />

        <Stack gap="lg" mt="lg">
          <TextInput
            label="Role Name"
            name="name"
            placeholder="Enter role name"
            value={roleDetails.name}
            onChange={handleChange}
            required
            size="md"
            radius="md"
          />

          <TextInput
            label="Full Name"
            name="full_name"
            placeholder="Enter full name of the role"
            value={roleDetails.full_name}
            onChange={handleChange}
            required
            size="md"
            radius="md"
          />

          <Select
            label="Type"
            name="type"
            placeholder="Select type of the role"
            value={roleDetails.type}
            onChange={(value) => setRoleDetails({ ...roleDetails, type: value })}
            size="md"
            data={[
              { value: 'academic', label: 'Academic Designation' },
              { value: 'administrative', label: 'Administrative Designation' },
            ]}
          />

          <Select
            label="Basic"
            name="basic"
            placeholder="Select whether the role is basic"
            value={roleDetails.basic ? "true" : "false"}
            onChange={(value) => setRoleDetails({ ...roleDetails, basic: value=="true"? true: false })}
            size="md"
            data={[
              { value: "false", label: 'False' },
              { value: "true", label: 'True' },
            ]}
          />

          <Group justify="flex-end" mt="sm">
            <Button ref={submitButtonRef} onClick={() => setIsOpen(true)}>
              Create Role
            </Button>
          </Group>
        </Stack>
      </Card>

      {/* Confirmation Modal */}
      <Modal
        opened={isOpen}
        onClose={() => setIsOpen(false)}
        title="Confirm Role Creation"
      >
        <Text>Are you sure you want to create this custom role?</Text>
        <Group justify="flex-end" mt="md">
          <Button variant="default" onClick={() => setIsOpen(false)}>
            Cancel
          </Button>
          <Button ref={confirmButtonRef} onClick={handleSubmit}>
            Confirm
          </Button>
        </Group>
      </Modal>

      {/* Validation Modal for empty fields */}
      <Modal
        opened={validationModalOpen}
        onClose={() => setValidationModalOpen(false)}
        title="Incomplete Fields"
      >
        <Text>You need to fill in all the fields before submitting the form.</Text>
        <Group justify="flex-end" mt="md">
          <Button onClick={() => setValidationModalOpen(false)}>OK</Button>
        </Group>
      </Modal>
    </Container>
  );
};

export default CreateCustomRolePage;
