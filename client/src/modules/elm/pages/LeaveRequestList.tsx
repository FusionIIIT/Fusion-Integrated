import { Container, Button, Card, Stack, Text } from "@mantine/core";
import { Link } from "react-router-dom";
import { PageHeader } from "../../../ui/components/PageHeader";

export default function LeaveRequestList() {
  return (
    <Container size="xl">
      <PageHeader
        title="Leave Requests"
        subtitle="Manage and view your leave requests"
        action={
          <Button component={Link} to="/elm/leave-requests/create">
            Apply for Leave
          </Button>
        }
      />
      <Card padding="lg" withBorder>
        <Stack>
          <Text c="dimmed">No leave requests found.</Text>
        </Stack>
      </Card>
    </Container>
  );
}
