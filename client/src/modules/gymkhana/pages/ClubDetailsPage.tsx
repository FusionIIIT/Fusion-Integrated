import { Badge, Button, Card, Group, Stack, Text, Title } from "@mantine/core";
import { Link, useNavigate, useParams } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";
import { clubs } from "../data";

export default function ClubDetailsPage() {
  const { clubId } = useParams();
  const navigate = useNavigate();
  const club = clubs.find((item) => item.id === clubId);

  if (!club) {
    return (
      <Stack gap="md">
        <Title order={2}>Club not found</Title>
        <Text c="dimmed">The requested club does not exist in the demo data.</Text>
        <Button component={Link} to="/gymkhana/clubs" variant="light">
          Back to Club Directory
        </Button>
      </Stack>
    );
  }

  return (
    <Stack gap="lg">
      <PageHeader
        title={club.name}
        subtitle="Club information and details"
        action={
          <Button variant="default" onClick={() => navigate(-1)}>
            Go Back
          </Button>
        }
      />

      <Card withBorder radius="md" padding="lg">
        <Stack gap="md">
          <Group>
            <Badge variant="light">{club.category}</Badge>
            <Badge color={club.status === "Active" ? "green" : "yellow"}>
              {club.status}
            </Badge>
          </Group>

          <div>
            <Title order={4} mb="xs">About the Club</Title>
            <Text c="dimmed">{club.description}</Text>
          </div>

          <div>
            <Title order={4} mb="xs">Club Information</Title>
            <Text size="sm">Members: {club.members}</Text>
            <Text size="sm">Coordinator: {club.coordinator}</Text>
            <Text size="sm">Faculty Councillor: {club.facultyCouncillor}</Text>
          </div>

          <Text c="dimmed" size="xs">
            Demo information — membership actions and live club records are not connected yet.
          </Text>

          <Group>
            <Button component={Link} to="/gymkhana/clubs" variant="light">
              Browse All Clubs
            </Button>
          </Group>
        </Stack>
      </Card>
    </Stack>
  );
}
