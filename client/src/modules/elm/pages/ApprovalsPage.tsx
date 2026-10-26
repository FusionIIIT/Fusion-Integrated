import { Alert, Container, Text } from "@mantine/core";
import { FaInfoCircle } from "react-icons/fa";

import { PageHeader } from "../../../ui/components/PageHeader";

export default function ApprovalsPage() {
  return (
    <Container size="md">
      <PageHeader title="Leave Approvals" />
      <Alert variant="light" color="blue" icon={<FaInfoCircle />} title="Not available in this MVP">
        <Text size="sm">
          Employees can submit and track requests, but authority routing and approve/reject
          actions have not been implemented. Submitted requests remain Pending. No approval
          decision is simulated or recorded by this screen.
        </Text>
      </Alert>
    </Container>
  );
}
