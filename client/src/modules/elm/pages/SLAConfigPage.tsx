import { useEffect, useState } from "react";
import {
  Button, Card, Container, Group, NumberInput, Select, Stack, Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { errorMessage } from "../../../lib/http";
import { useSaveSLAThresholds, useSLAThresholds } from "../api/hooks";
import type { SLAThresholdConfig } from "../api/types";

const DEFAULTS: SLAThresholdConfig = {
  reminder_threshold_minutes: 60,
  escalation_threshold_minutes: 1440,
  escalation_action: "notify",
};

export default function SLAConfigPage() {
  const configQuery = useSLAThresholds();
  const save = useSaveSLAThresholds();
  const [config, setConfig] = useState(DEFAULTS);

  useEffect(() => {
    if (configQuery.data) setConfig(configQuery.data);
  }, [configQuery.data]);

  if (configQuery.error) {
    return <Container size="md"><ErrorState error={configQuery.error} /></Container>;
  }

  function submit() {
    save.mutate(config, {
      onSuccess: () => notifications.show({
        color: "green",
        title: "SLA settings saved",
        message: "The new thresholds will apply to actionable workflow tasks.",
      }),
      onError: (error) => notifications.show({
        color: "red",
        title: "Could not save SLA settings",
        message: errorMessage(error),
      }),
    });
  }

  return (
    <Container size="md">
      <PageHeader
        title="SLA Thresholds"
        subtitle="Set reminders and escalation for actionable workflow tasks"
      />
      <Card withBorder>
        <Stack>
          <NumberInput
            label="Reminder threshold (minutes)"
            min={1}
            value={config.reminder_threshold_minutes}
            onChange={(value) => setConfig((current) => ({
              ...current,
              reminder_threshold_minutes: Number(value) || 1,
            }))}
          />
          <NumberInput
            label="Escalation threshold (minutes)"
            min={2}
            value={config.escalation_threshold_minutes}
            onChange={(value) => setConfig((current) => ({
              ...current,
              escalation_threshold_minutes: Number(value) || 2,
            }))}
          />
          <Select
            label="Escalation action"
            data={[
              { value: "notify", label: "Notify the responsible authority" },
              { value: "route_change", label: "Change routing / responsibility" },
              { value: "none", label: "No escalation action" },
            ]}
            value={config.escalation_action}
            onChange={(value) => {
              if (value) {
                setConfig((current) => ({
                  ...current,
                  escalation_action: value as SLAThresholdConfig["escalation_action"],
                }));
              }
            }}
          />
          {config.escalation_threshold_minutes
            <= config.reminder_threshold_minutes && (
            <Text c="red" size="sm">
              The escalation threshold must be greater than the reminder threshold.
            </Text>
          )}
          <Group justify="flex-end">
            <Button
              onClick={submit}
              loading={save.isPending}
              disabled={
                config.escalation_threshold_minutes
                <= config.reminder_threshold_minutes
              }
            >
              Save thresholds
            </Button>
          </Group>
        </Stack>
      </Card>
    </Container>
  );
}
