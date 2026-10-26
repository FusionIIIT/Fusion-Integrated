import { Badge, Card, Grid, Group, Stack, Text, ThemeIcon } from "@mantine/core";
import { FaBook, FaCheck, FaTimes } from "react-icons/fa";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveTypes } from "../api/hooks";

export default function LeavePoliciesPage() {
  const { data: leaveTypes = [], isLoading } = useLeaveTypes();

  return (
    <div>
      <PageHeader
        title="Leave Categories & Policies"
        subtitle="Current configured policy parameters and baseline entitlements (BR-EL-001 through BR-EL-009)"
      />

      <Grid>
        {leaveTypes.map((t) => (
          <Grid.Col key={t.id} span={{ base: 12, md: 6 }}>
            <Card withBorder padding="md" radius="md">
              <Stack gap="xs">
                <Group justify="space-between">
                  <Group gap="xs">
                    <ThemeIcon size="md" variant="light" color="indigo">
                      <FaBook size={14} />
                    </ThemeIcon>
                    <Text fw={600} size="md">
                      {t.code} — {t.name}
                    </Text>
                  </Group>
                  <Badge variant="filled" color="blue">
                    {t.max_days_per_year} days/yr
                  </Badge>
                </Group>

                <Grid mt="xs">
                  <Grid.Col span={6}>
                    <Text size="xs" c="dimmed">Continuous-Day Counting</Text>
                    <Group gap={4} mt={2}>
                      {t.is_continuous_count ? (
                        <>
                          <FaCheck size={12} color="green" />
                          <Text size="xs">Includes weekends & holidays</Text>
                        </>
                      ) : (
                        <>
                          <FaTimes size={12} color="gray" />
                          <Text size="xs">Working days only</Text>
                        </>
                      )}
                    </Group>
                  </Grid.Col>

                  <Grid.Col span={6}>
                    <Text size="xs" c="dimmed">Year-End Carry Forward</Text>
                    <Group gap={4} mt={2}>
                      {t.carries_forward ? (
                        <>
                          <FaCheck size={12} color="green" />
                          <Text size="xs">Carries forward</Text>
                        </>
                      ) : (
                        <>
                          <FaTimes size={12} color="orange" />
                          <Text size="xs">{t.code === "VL" ? "Converts 2:1 to EL" : "Lapses at year-end"}</Text>
                        </>
                      )}
                    </Group>
                  </Grid.Col>

                  <Grid.Col span={6}>
                    <Text size="xs" c="dimmed">Applicability Scope</Text>
                    <Text size="xs" fw={500}>
                      {t.is_faculty_only ? "Faculty Only" : t.is_non_faculty_only ? "Staff (Non-Faculty) Only" : "All Employees"}
                    </Text>
                  </Grid.Col>

                  <Grid.Col span={6}>
                    <Text size="xs" c="dimmed">Medical Evidence</Text>
                    <Text size="xs" fw={500}>
                      {t.requires_document ? "Medical Certificate Required" : "Not Required"}
                    </Text>
                  </Grid.Col>
                </Grid>
              </Stack>
            </Card>
          </Grid.Col>
        ))}
      </Grid>
    </div>
  );
}
