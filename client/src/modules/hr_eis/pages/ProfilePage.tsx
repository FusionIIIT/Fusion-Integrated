import { useState } from "react";
import {
  Alert,
  Button,
  Container,
  Group,
  Loader,
  Stack,
  Title,
} from "@mantine/core";
import { FaPlus, FaExclamationCircle } from "react-icons/fa";
import { useMyProfile } from "../api/hooks";
import { ProfileHeader } from "../components/ProfileHeader";
import { WorkExperienceList } from "../components/WorkExperienceList";
import { WorkExperienceModal } from "../components/WorkExperienceModal";

export default function ProfilePage() {
  const { data: profile, isLoading, error } = useMyProfile();
  const [modalOpened, setModalOpened] = useState(false);

  if (isLoading) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" py="xl">
          <Loader size="lg" />
        </Group>
      </Container>
    );
  }

  if (error || !profile) {
    return (
      <Container size="lg" py="xl">
        <Alert
          icon={<FaExclamationCircle size={16} />}
          title="Profile Not Found"
          color="yellow"
          radius="md"
        >
          No Employee Information System profile was found for your account. If you are an active employee, please contact the HR / Establishment section to initialize your PF record.
        </Alert>
      </Container>
    );
  }

  return (
    <Container size="lg" py="xl">
      <Stack gap="xl">
        <ProfileHeader profile={profile} />

        <Group justify="space-between" align="center">
          <div>
            <Title order={4}>Work Experience History</Title>
          </div>
          <Button
            leftSection={<FaPlus size={14} />}
            onClick={() => setModalOpened(true)}
          >
            Add Experience
          </Button>
        </Group>

        <WorkExperienceList experiences={profile.experiences ?? []} />

        <WorkExperienceModal
          opened={modalOpened}
          onClose={() => setModalOpened(false)}
        />
      </Stack>
    </Container>
  );
}
