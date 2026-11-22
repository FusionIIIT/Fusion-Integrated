import { useEffect, useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  NumberInput,
  Stack,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaSave } from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { adminApi } from "../api/client";

export default function SystemConfigPage() {
  const { can } = useAuth();
  const canChange = can("system_admin.config.change");

  const [loading, setLoading] = useState(false);
  const [params, setParams] = useState<Record<string, string>>({
    bulk_operation_limit: "500",
    session_timeout_minutes: "30",
    archival_retention_years: "7",
    max_login_attempts: "5",
  });

  useEffect(() => {
    adminApi
      .getParameters()
      .then((data) => {
        if (data && Object.keys(data).length > 0) {
          setParams((prev) => ({ ...prev, ...data }));
        }
      })
      .catch((err) => {
        console.error("Failed to load parameters", err);
      });
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      const updated = await adminApi.updateParameters(params);
      setParams((prev) => ({ ...prev, ...updated }));
      notifications.show({
        color: "green",
        message: "System configuration parameters updated successfully.",
      });
    } catch (err: unknown) {
      notifications.show({
        color: "red",
        message: "Failed to update configuration: " + String(err),
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container size="md" py="lg">
      <PageHeader
        title="System Parameters & Governance Bounds"
        subtitle="Configure institutional thresholds within authorized Super Admin boundaries."
      />

      <Card withBorder padding="lg" radius="md">
        <Stack gap="md">
          <NumberInput
            label="Bulk Operation Batch Limit (BR-SA-030)"
            description="Maximum number of user records allowed per batch creation (Max: 1000)."
            min={1}
            max={1000}
            value={parseInt(params.bulk_operation_limit || "500", 10)}
            onChange={(val) => setParams({ ...params, bulk_operation_limit: String(val || 500) })}
            disabled={!canChange}
          />

          <NumberInput
            label="Administrative Session Timeout (Minutes)"
            description="Inactivity period before requiring re-authentication (5 to 1440 minutes)."
            min={5}
            max={1440}
            value={parseInt(params.session_timeout_minutes || "30", 10)}
            onChange={(val) => setParams({ ...params, session_timeout_minutes: String(val || 30) })}
            disabled={!canChange}
          />

          <NumberInput
            label="Statutory Archival Retention Period (Years) (BR-SA-021)"
            description="Minimum retention duration before permanent purge eligibility can be requested (1 to 50 years)."
            min={1}
            max={50}
            value={parseInt(params.archival_retention_years || "7", 10)}
            onChange={(val) => setParams({ ...params, archival_retention_years: String(val || 7) })}
            disabled={!canChange}
          />

          <NumberInput
            label="Maximum Failed Login Attempts (BR-SA-034)"
            description="Number of consecutive authentication failures triggering account alert (3 to 10)."
            min={3}
            max={10}
            value={parseInt(params.max_login_attempts || "5", 10)}
            onChange={(val) => setParams({ ...params, max_login_attempts: String(val || 5) })}
            disabled={!canChange}
          />

          {canChange && (
            <Group justify="flex-end" mt="md">
              <Button leftSection={<FaSave />} loading={loading} onClick={handleSave}>
                Save System Parameters
              </Button>
            </Group>
          )}
        </Stack>
      </Card>
    </Container>
  );
}
