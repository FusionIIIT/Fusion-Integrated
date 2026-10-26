import {
  Alert,
  Badge,
  Card,
  Container,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Table,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  FaCalendarCheck,
  FaClock,
  FaHandsHelping,
  FaInfoCircle,
  FaLayerGroup,
  FaShieldAlt,
  FaUserTie,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeaveTypes } from "../api/hooks";

export default function PolicyPage() {
  const { can } = useAuth();
  const canManage = can("leave.type.manage");
  const { data: leaveTypes, error } = useLeaveTypes();

  if (error) {
    return (
      <Container size="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  return (
    <Container size="xl">
      <PageHeader
        title="Leave Policy & Entitlement Guidelines"
        subtitle="Authoritative leave categories, entitlement quotas, accounting rules, and approval hierarchies."
      />

      {canManage && (
        <Alert
          color="blue"
          icon={<FaInfoCircle />}
          mb="lg"
          title="Policy Administrator Notice"
        >
          <Text size="sm">
            Leave policies in this baseline are configured system parameters. Changes to quota ceilings,
            carry-forward maximums, and holiday calendars are applied directly across the active academic year.
          </Text>
        </Alert>
      )}

      {/* Summary Stat Grid */}
      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} mb="lg" spacing="md">
        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">Active Categories</Text>
              <Text size="xl" fw={800} c="blue">{leaveTypes?.length ?? 6}</Text>
            </div>
            <ThemeIcon color="blue" variant="light" size="lg">
              <FaLayerGroup />
            </ThemeIcon>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">CL, RH, EL, SCL, COL, VL</Text>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">Casual Leave (CL)</Text>
              <Text size="xl" fw={800} c="teal">8.0 Days</Text>
            </div>
            <ThemeIcon color="teal" variant="light" size="lg">
              <FaCalendarCheck />
            </ThemeIcon>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">Working-day count; lapses at year-end</Text>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">Earned Leave (EL)</Text>
              <Text size="xl" fw={800} c="indigo">30.0 Days</Text>
            </div>
            <ThemeIcon color="indigo" variant="light" size="lg">
              <FaClock />
            </ThemeIcon>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">Continuous count; carries forward (max 300)</Text>
        </Paper>

        <Paper withBorder p="md" radius="md">
          <Group justify="space-between">
            <div>
              <Text size="xs" c="dimmed">Restricted Holiday (RH)</Text>
              <Text size="xl" fw={800} c="orange">2.0 Days</Text>
            </div>
            <ThemeIcon color="orange" variant="light" size="lg">
              <FaHandsHelping />
            </ThemeIcon>
          </Group>
          <Text size="xs" c="dimmed" mt="xs">2 festival days per calendar year</Text>
        </Paper>
      </SimpleGrid>

      {/* Main Policy Matrix Table */}
      <Card withBorder padding="lg" radius="md" mb="lg">
        <Text fw={700} size="md" mb="sm">
          Leave Categories & Rule Matrix
        </Text>
        <Table.ScrollContainer minWidth={800}>
          <Table verticalSpacing="sm" striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Code</Table.Th>
                <Table.Th>Category Name</Table.Th>
                <Table.Th>Counting Basis</Table.Th>
                <Table.Th>Half-Day</Table.Th>
                <Table.Th>Substitute</Table.Th>
                <Table.Th>Year-End Treatment</Table.Th>
                <Table.Th>Approval Path</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {leaveTypes?.map((t) => (
                <Table.Tr key={t.code}>
                  <Table.Td>
                    <Badge variant="filled" color="blue">
                      {t.code}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text fw={600} size="sm">{t.name}</Text>
                    {t.requires_medical_certificate && (
                      <Badge size="xs" color="red" variant="outline">
                        Medical Certificate
                      </Badge>
                    )}
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="light" color={t.is_continuous_count ? "indigo" : "teal"} size="sm">
                      {t.is_continuous_count ? "Continuous (Calendar Days)" : "Working Days Only"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline" color={t.allows_half_day ? "green" : "gray"} size="sm">
                      {t.allows_half_day ? "Allowed (FN/AN)" : "Full Day Only"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Badge variant="outline" color={t.requires_substitute ? "orange" : "gray"} size="sm">
                      {t.requires_substitute ? "Mandatory" : "Not Required"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs" fw={600} c={t.carries_forward ? "green" : "gray"}>
                      {t.carries_forward ? "Carries Forward" : "Lapses at Year-End"}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Text size="xs">
                      {["CL", "RH"].includes(t.code) ? "Unit Head (Final)" : "Unit Head → Sanctioning Authority"}
                    </Text>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Table.ScrollContainer>
      </Card>

      {/* Workflow Architecture & Key Rules */}
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        <Card withBorder padding="lg" radius="md">
          <Group gap="xs" mb="sm">
            <ThemeIcon color="blue" size="md">
              <FaUserTie />
            </ThemeIcon>
            <Title order={4}>Approval Authority Hierarchy</Title>
          </Group>
          <Stack gap="xs">
            <Paper p="xs" withBorder bg="var(--mantine-color-gray-0)">
              <Text fw={700} size="xs" c="blue">Casual Leave & Restricted Holiday (CL, RH)</Text>
              <Text size="xs">
                The applicant’s Unit Head (Head of Department / Section) is the <strong>final authority</strong>.
                Decision options are direct Approve or Reject.
              </Text>
            </Paper>

            <Paper p="xs" withBorder bg="var(--mantine-color-gray-0)">
              <Text fw={700} size="xs" c="indigo">Higher Sanction Leave (EL, SCL, COL, VL)</Text>
              <Text size="xs">
                The Unit Head records a <strong>Recommendation</strong> (Recommended or Not Recommended).
                The request then routes through the configured administrative hierarchy (Dean, Registrar, Director)
                for final sanction.
              </Text>
            </Paper>

            <Paper p="xs" withBorder bg="var(--mantine-color-gray-0)">
              <Text fw={700} size="xs" c="teal">Station Leave Permission</Text>
              <Text size="xs">
                Required whenever leaving headquarters. Captured as an integrated attribute of the primary leave application.
              </Text>
            </Paper>
          </Stack>
        </Card>

        <Card withBorder padding="lg" radius="md">
          <Group gap="xs" mb="sm">
            <ThemeIcon color="indigo" size="md">
              <FaShieldAlt />
            </ThemeIcon>
            <Title order={4}>Lifecycle Safeguards & Integrity</Title>
          </Group>
          <Stack gap="xs">
            <Paper p="xs" withBorder bg="var(--mantine-color-gray-0)">
              <Text fw={700} size="xs" c="orange">Withdrawal vs Cancellation</Text>
              <Text size="xs">
                Pending requests may be withdrawn immediately before final sanction. Approved leave cannot be withdrawn;
                it must be cancelled before the start date via hierarchical review.
              </Text>
            </Paper>

            <Paper p="xs" withBorder bg="var(--mantine-color-gray-0)">
              <Text fw={700} size="xs" c="grape">Extension of Ongoing Leave</Text>
              <Text size="xs">
                Employees on ongoing EL, COL, or VL may request an extension. The extension requires substitute consent
                and hierarchical sanction; only the incremental period is debited upon approval.
              </Text>
            </Paper>

            <Paper p="xs" withBorder bg="var(--mantine-color-gray-0)">
              <Text fw={700} size="xs" c="teal">Duty Resumption & Reconciliation</Text>
              <Text size="xs">
                Following EL/COL/VL, employees must submit duty resumption. If resumption is early or late, leave balances
                are automatically adjusted upon sanctioning authority verification.
              </Text>
            </Paper>
          </Stack>
        </Card>
      </SimpleGrid>
    </Container>
  );
}
