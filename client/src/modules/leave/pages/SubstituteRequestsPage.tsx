import { useState } from "react";
import {
  ActionIcon, Button, Card, Container, Group, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaCheck, FaTimes } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { ErrorState } from "../../../ui/components/ErrorState";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useRespondToSubstitute, useNominateReplacement } from "../api/hooks";

export default function SubstituteRequestsPage() {
  const respondMutation = useRespondToSubstitute();
  const nominateMutation = useNominateReplacement();
  const [requestId, setRequestId] = useState<number | null>(null);

  if (respondMutation.isPending || nominateMutation.isPending) {
    return (
      <Container size="xl">
        <PageHeader title="Substitute Requests" subtitle="Manage substitute requests" />
        <Card padding="lg">
          <Text>Processing...</Text>
        </Card>
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader title="Substitute Requests" subtitle="Requests addressed to you" />
      {respondMutation.isPending || nominateMutation.isPending ? (
        <Card padding="lg">
          <Text>Processing...</Text>
        </Card>
      ) : (
        <>
          <Card padding="lg" mb="md">
            <Text fw={600}>Substitute Requests</Text>
            <Text size="sm" c="dimmed">
              Manage requests for substitute users.
            </Text>
          </Card>

          <Card padding="lg">
            <Stack gap="md">
              {/* Placeholder for actual request list */}
              <Text>No active substitute requests</Text>
            </Stack>
          </Card>
        </>
      )}
    </Container>
  );
}
