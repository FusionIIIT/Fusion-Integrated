import { useState } from "react";
import {
  Alert, Badge, Card, Container, Group, Select, Text, NumberInput,
  Button, notifications, FaClock, FaInfoCircle,
} from "@mantine/core";
import { useSLATrusts, useYearEndProcessing } from "../api/hooks";
import { useNavigate } from "react-router-dom";

/** EL-UC-018: Configure Workflow SLA Thresholds — Configure reminder and
 * escalation thresholds for SLA-controlled actionable workflow tasks. */
export default function SLAConfigPage() {
  const navigate = useNavigate();
  const slaQuery = useSLATrusts();
  const yearEndMutation = useYearEndProcessing();

  const [thresholds, setThresholds] = useState<SLAThresholdConfig>({
    reminder_threshold_minutes: 60,
    escalation_threshold_minutes: 1440,
    escalation_action: "notify",
  });

  const [isSaving, setIsSaving] = useState(false);

  if (slaQuery.error) {
    return (
      <Container size="md">
        <ErrorState error={slaQuery.error} />
      </Container>
    );
  }

  const { reminder_threshold_minutes, escalation_threshold_minutes, escalation_action } = thresholds;

  const onSave = async () => {
    setIsSaving(true);
    try {
      const response = await fetch("/api/v1/elm/sla/thresholds", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(thresholds),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to save SLA thresholds");
      }

      notifications.show({
        color: "green",
        title: "SLA thresholds updated",
        message: "SLA reminder and escalation thresholds have been saved.",
      });
    } catch (e: any) {
      notifications.show({
        color: "red",
        title: "Could not save SLA thresholds",
        message: e.message,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const onProcessYearEnd = async () => {
    setIsSaving(true); // Reusing isSaving
    try {
      const response = await fetch("/api/v1/elm/year-end", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to execute year-end processing");
      }

      const result: any = await response.json();
      notifications.show({
        color: "green",
        title: "Year-end processing completed",
        message: `Processed year-end for ${result.summary.categories_processed} leave categories with ${result.summary.total_transactions} transactions.`,
      });
    } catch (e: any) {
      notifications.show({
        color: "red",
        title: "Year-end processing failed",
        message: e.message,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Container size="md">
      <PageHeader title="SLA Threshold Configuration" />

      {slaQuery.error && (
        <Alert variant="light" color="red" icon={<FaInfoCircle />}>
          {slaQuery.error.message}
        </Alert>
      )}

      <Card padding="lg">
        <Group gap="sm">
          <Text fw={600}>SLA Reminder Threshold</Text>
          <Select
            label="Reminder threshold (minutes)"
            data={[
              { value: 30, label: "30 minutes" },
              { value: 60, label: "60 minutes (1 hour)" },
              { value: 120, label: "120 minutes (2 hours)" },
              { value: 360, label: "360 minutes (6 hours)" },
              { value: 720, label: "720 minutes (12 hours)" },
              { value: 1440, label: "1440 minutes (24 hours)" },
            ]}
            value={reminder_threshold_minutes}
            onChange={(v) =>
              setThresholds({ ...thresholds, reminder_threshold_minutes: parseInt(v) })}
          />
          <Text size="xs" c="dimmed">
            When an actionable task reaches this threshold, a reminder is issued
            if the task is still pending.
          </Text>
        </Group>

        <Group gap="sm">
          <Text fw={600}>SLA Escalation Threshold</Text>
          <Select
            label="Escalation threshold (minutes)"
            data={[
              { value: 60, label: "60 minutes (1 hour)" },
              { value: 180, label: "180 minutes (3 hours)" },
              { value: 360, label: "360 minutes (6 hours)" },
              { value: 720, label: "720 minutes (12 hours)" },
              { value: 1440, label: "1440 minutes (24 hours)" },
              { value: 2880, label: "2880 minutes (48 hours)" },
              { value: 4320, label: "4320 minutes (72 hours)" },
              { value: 10080, label: "10080 minutes (7 days)" },
            ]}
            value={escalation_threshold_minutes}
            onChange={(v) =>
              setThresholds({ ...thresholds, escalation_threshold_minutes: parseInt(v) })}
          />
          <Text size="xs" c="dimmed">
            When an actionable task remains pending past this threshold, the configured
            escalation action is performed (notification or routing change).
          </Text>
        </Group>

        <Group gap="sm">
          <Text fw={600}>Escalation Action</Text>
          <Select
            label="Escalation action"
            data={[
              { value: "notify", label: "Notify only (no workflow transition)" },
              { value: "route_change", label: "Change routing/responsibility" },
              { value: "none", label: "No escalation action" },
            ]}
            value={escalation_action}
            onChange={(v) =>
              setThresholds({ ...thresholds, escalation_action: v })}
          />
          <Text size="xs" c="dimmed">
            "Notify only" logs a reminder but does not change the workflow.
            "Route change" automatically reassigns the task to a configured higher
            or responsible authority.
          </Text>
        </Group>

        <Group gap="sm" justify="flex-end">
          <Button
            loading={isSaving}
            onClick={onSave}
            variant="filled"
          >
            Save SLA Thresholds
          </Button>

          {/* Year-end processing button (admin only) */}
          <Button
            loading={isSaving || false}
            onClick={onProcessYearEnd}
            variant="outline"
            style={{ marginLeft: 8 }}
          >
            Year-End Processing
          </Button>
        </Group>
      </Card>
    </Container>
  );
}

/** Placeholder ErrorState component */
function ErrorState({ error }: { error: any }) {
  return (
    <Card padding="lg" color="red">
      <Text fw={600} mb="xs">Error</Text>
      <Text c="red">{error?.message || error || "Unknown error"}</Text>
    </Card>
  );
}