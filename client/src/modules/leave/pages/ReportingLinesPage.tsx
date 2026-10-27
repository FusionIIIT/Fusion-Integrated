import { useState } from "react";
import { Button, Card, Container, Group, NumberInput, Stack, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage, errorStatus } from "../../../lib/http";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useReportingLine, useSetReportingLine } from "../api";

export default function ReportingLinesPage() {
  const [lookupId, setLookupId] = useState("");
  const [userId, setUserId] = useState<number | null>(null);
  const [unitHeadId, setUnitHeadId] = useState("");
  const [establishmentId, setEstablishmentId] = useState("");
  const [sanctioningId, setSanctioningId] = useState("");

  const line = useReportingLine(userId);
  const save = useSetReportingLine();

  const handleLoad = async () => {
    if (!lookupId) return;
    const newUserId = Number(lookupId);
    if (isNaN(newUserId)) return;

    setUserId(newUserId);
    setUnitHeadId("");
    setEstablishmentId("");
    setSanctioningId("");

    try {
      await line.refetch();
      if (line.data) {
        const data = line.data;
        setUnitHeadId(String(data.unit_head_id || ""));
        setEstablishmentId(String(data.establishment_id || ""));
        setSanctioningId(String(data.sanctioning_authority_id || ""));
      }
    } catch (e) {
      // Handle error below if needed, but refetch usually handles display
    }
  };

  const handleSave = () => {
    if (!userId || !unitHeadId) {
      notifications.show({
        color: "red",
        title: "Missing Information",
        message: "Please select a User ID and a Unit Head.",
      });
      return;
    }

    save.mutate(
      {
        user_id: userId,
        unit_head_id: Number(unitHeadId),
        establishment_id: establishmentId ? Number(establishmentId) : null,
        sanctioning_authority_id: sanctioningId ? Number(sanctioningId) : null,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Saved",
            message: `Reporting line for user ${userId} saved.`,
          });
        },
        onError: (e) => {
          notifications.show({
            color: "red",
            title: "Could not save",
            message: errorMessage(e),
          });
        },
      }
    );
  };

  const handle404 = () => {
    if (line.error && errorStatus(line.error) === 404) {
      return (
        <Text c="dimmed" size="sm" mt={8}>
          No reporting line yet for user {userId}. Fill in the fields below and save.
        </Text>
      );
    }
    return null;
  };

  return (
    <Container size="sm">
      <PageHeader title="Reporting Lines" subtitle="Who decides each person's leave" />
      <Card padding="lg">
        <Group justify="space-between" align="flex-end" mb={20}>
          <NumberInput
            label="User id"
            value={lookupId}
            onChange={(value) => setLookupId(String(value))}
            placeholder="Enter user ID to load"
          />
          <Button onClick={handleLoad} disabled={!lookupId} loading={line.isPending}>
            Load
          </Button>
        </Group>

        {handle404()}

        <Stack gap={10}>
          <NumberInput
            label="Unit Head (user id)"
            value={unitHeadId}
            onChange={(value) => setUnitHeadId(String(value))}
            placeholder="Enter unit head user ID"
            required
          />

          <NumberInput
            label="Establishment officer (user id, optional)"
            value={establishmentId}
            onChange={(value) => setEstablishmentId(String(value))}
            placeholder="Enter establishment officer user ID"
          />

          <NumberInput
            label="Sanctioning Authority (user id, optional)"
            value={sanctioningId}
            onChange={(value) => setSanctioningId(String(value))}
            placeholder="Enter sanctioning authority user ID"
          />

          <Button
            type="button"
            onClick={handleSave}
            disabled={!userId || !unitHeadId}
            loading={save.isPending}
          >
            Save
          </Button>
        </Stack>
      </Card>
    </Container>
  );
}
