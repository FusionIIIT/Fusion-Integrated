import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Grid,
  Group,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
  FaBuilding,
  FaBullhorn,
  FaCalendarAlt,
  FaCheck,
  FaClipboardCheck,
  FaClipboardList,
  FaEdit,
  FaThLarge,
  FaTimes,
  FaUserShield,
  FaUserTie,
  FaUsers,
} from "react-icons/fa";
import { Link } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useDecideDetailChange,
  useDepartmentChanges,
  useDepartmentDetails,
  useDepartments,
} from "../api/hooks";
import { ProposeDetailChangeModal } from "../components/ProposeDetailChangeModal";
import { DepartmentStatusBadge } from "../components/DepartmentStatusBadge";

export default function OverviewPage() {
  const { can } = useAuth();
  const { data: departments, isPending, error } = useDepartments();
  const defaultDept = departments?.[0];
  const deptId = defaultDept?.id;

  const { data: detailsList } = useDepartmentDetails(deptId);
  const { data: changes } = useDepartmentChanges(deptId);
  const decideChange = useDecideDetailChange();

  const [proposing, setProposing] = useState(false);

  const canPropose = can("department.detail.propose") || can("department.detail.update");
  const canDecide = can("department.detail.update");

  if (error) return <Container size="lg"><ErrorState error={error} /></Container>;

  const detail = detailsList?.[0];
  const pendingChanges = (changes || []).filter((c) => c.status === "pending");

  const handleDecide = async (id: number, status: "approved" | "rejected") => {
    try {
      await decideChange.mutateAsync({ id, status });
      notifications.show({
        title: `Proposal ${status}`,
        message: `The proposal has been ${status}.`,
        color: status === "approved" ? "teal" : "red",
      });
    } catch {
      notifications.show({
        title: "Action failed",
        message: "Could not update proposal status.",
        color: "red",
      });
    }
  };

  return (
    <Container size="lg">
      <PageHeader
        title={defaultDept ? defaultDept.name : "Department Overview"}
        subtitle={
          defaultDept
            ? `${defaultDept.code} · ${defaultDept.description || "Official Department Portal"}`
            : "Academic & Administrative Portal"
        }
        action={
          canPropose && deptId ? (
            <Button
              leftSection={<FaEdit size={13} />}
              onClick={() => setProposing(true)}
            >
              Propose Detail Change
            </Button>
          ) : undefined
        }
      />

      {isPending && <Text c="dimmed">Loading department info…</Text>}

      {defaultDept && (
        <Stack gap="lg">
          {/* Quick Stats & Identity */}
          <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
            <Card padding="md" withBorder>
              <Group>
                <ThemeIcon size="lg" radius="md" color="blue" variant="light">
                  <FaUserTie size={18} />
                </ThemeIcon>
                <div>
                  <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                    Head of Department (HOD)
                  </Text>
                  <Text fw={600}>
                    {defaultDept.head_user_id
                      ? `User #${defaultDept.head_user_id}`
                      : "Not Assigned"}
                  </Text>
                </div>
              </Group>
            </Card>

            <Card padding="md" withBorder>
              <Group>
                <ThemeIcon size="lg" radius="md" color="teal" variant="light">
                  <FaUserShield size={18} />
                </ThemeIcon>
                <div>
                  <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                    Department Administrator
                  </Text>
                  <Text fw={600}>
                    {defaultDept.admin_user_id
                      ? `User #${defaultDept.admin_user_id}`
                      : "Not Assigned"}
                  </Text>
                </div>
              </Group>
            </Card>

            <Card padding="md" withBorder>
              <Group>
                <ThemeIcon size="lg" radius="md" color="violet" variant="light">
                  <FaBuilding size={18} />
                </ThemeIcon>
                <div>
                  <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                    Department Code
                  </Text>
                  <Text fw={600}>{defaultDept.code}</Text>
                </div>
              </Group>
            </Card>
          </SimpleGrid>

          {/* Core Policies & Information */}
          <Card padding="lg" withBorder>
            <Title order={4} mb="xs">
              Core Policies & Guidelines
            </Title>
            <Text size="sm" c="dimmed" style={{ whiteSpace: "pre-wrap" }}>
              {detail?.core_policies ||
                "Standard institute academic regulations and lab conduct guidelines apply. Timely submission of stock requests and lab requisitions is required."}
            </Text>
          </Card>

          {/* Pending Changes for Decision */}
          {pendingChanges.length > 0 && (
            <Card padding="lg" withBorder style={{ borderColor: "var(--mantine-color-yellow-4)" }}>
              <Title order={4} mb="sm">
                Pending Policy Change Proposals ({pendingChanges.length})
              </Title>
              <Stack gap="sm">
                {pendingChanges.map((ch) => (
                  <Card key={ch.id} padding="sm" withBorder>
                    <Group justify="space-between" wrap="nowrap">
                      <div>
                        <Group gap="xs">
                          <Text fw={600} size="sm">
                            Field: {ch.field_name}
                          </Text>
                          <DepartmentStatusBadge status={ch.status} />
                        </Group>
                        <Text size="xs" mt={4} style={{ whiteSpace: "pre-wrap" }}>
                          {ch.proposed_value}
                        </Text>
                        <Text size="xs" c="dimmed" mt={2}>
                          Proposed by User #{ch.proposed_by_user_id} ·{" "}
                          {new Date(ch.created_at).toLocaleDateString()}
                        </Text>
                      </div>

                      {canDecide && (
                        <Group gap="xs">
                          <Button
                            size="xs"
                            color="teal"
                            leftSection={<FaCheck size={10} />}
                            loading={decideChange.isPending}
                            onClick={() => handleDecide(ch.id, "approved")}
                          >
                            Approve
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="light"
                            leftSection={<FaTimes size={10} />}
                            loading={decideChange.isPending}
                            onClick={() => handleDecide(ch.id, "rejected")}
                          >
                            Reject
                          </Button>
                        </Group>
                      )}
                    </Group>
                  </Card>
                ))}
              </Stack>
            </Card>
          )}

          {/* Quick Navigation Cards */}
          <Title order={4} mt="sm">
            Department Modules
          </Title>
          <Grid>
            <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
              <Card padding="md" withBorder component={Link} to="/department/announcements" style={{ textDecoration: "none" }}>
                <Group>
                  <ThemeIcon size="xl" radius="md" color="indigo" variant="light">
                    <FaBullhorn size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600}>Announcements</Text>
                    <Text size="xs" c="dimmed">Notices, exams & schedules</Text>
                  </div>
                </Group>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
              <Card padding="md" withBorder component={Link} to="/department/inventory" style={{ textDecoration: "none" }}>
                <Group>
                  <ThemeIcon size="xl" radius="md" color="cyan" variant="light">
                    <FaClipboardList size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600}>Inventory & Stock</Text>
                    <Text size="xs" c="dimmed">Stock requisitions & items</Text>
                  </div>
                </Group>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
              <Card padding="md" withBorder component={Link} to="/department/feedback" style={{ textDecoration: "none" }}>
                <Group>
                  <ThemeIcon size="xl" radius="md" color="orange" variant="light">
                    <FaClipboardCheck size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600}>Feedback & Grievance</Text>
                    <Text size="xs" c="dimmed">Confidential department input</Text>
                  </div>
                </Group>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
              <Card padding="md" withBorder component={Link} to="/department/timetable" style={{ textDecoration: "none" }}>
                <Group>
                  <ThemeIcon size="xl" radius="md" color="teal" variant="light">
                    <FaCalendarAlt size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600}>Timetable</Text>
                    <Text size="xs" c="dimmed">Classroom & lab scheduling</Text>
                  </div>
                </Group>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
              <Card padding="md" withBorder component={Link} to="/department/faculty-staff" style={{ textDecoration: "none" }}>
                <Group>
                  <ThemeIcon size="xl" radius="md" color="grape" variant="light">
                    <FaUsers size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600}>Faculty & Staff</Text>
                    <Text size="xs" c="dimmed">Personnel directory & profiles</Text>
                  </div>
                </Group>
              </Card>
            </Grid.Col>

            <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
              <Card padding="md" withBorder component={Link} to="/department/resources" style={{ textDecoration: "none" }}>
                <Group>
                  <ThemeIcon size="xl" radius="md" color="blue" variant="light">
                    <FaThLarge size={20} />
                  </ThemeIcon>
                  <div>
                    <Text fw={600}>Lab Resources</Text>
                    <Text size="xs" c="dimmed">Equipment, kits & labs</Text>
                  </div>
                </Group>
              </Card>
            </Grid.Col>
          </Grid>
        </Stack>
      )}

      {deptId && (
        <ProposeDetailChangeModal
          opened={proposing}
          onClose={() => setProposing(false)}
          departmentId={deptId}
        />
      )}
    </Container>
  );
}
