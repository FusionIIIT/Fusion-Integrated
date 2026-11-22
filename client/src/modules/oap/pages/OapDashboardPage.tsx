import { Alert, Button, Card, Container, Grid, Group, Loader, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useBonafides,
  useBranchChanges,
  useLeaves,
  useNoDues,
} from "../api/hooks";

export default function OapDashboardPage() {
  const { can } = useAuth();
  const leavesQuery = useLeaves();
  const bonafidesQuery = useBonafides();
  const noDuesQuery = useNoDues();
  const branchChangesQuery = useBranchChanges();

  const isPending =
    leavesQuery.isPending ||
    bonafidesQuery.isPending ||
    noDuesQuery.isPending ||
    branchChangesQuery.isPending;

  const error =
    leavesQuery.error ||
    bonafidesQuery.error ||
    noDuesQuery.error ||
    branchChangesQuery.error;

  if (isPending) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" p="xl" data-testid="loading-state">
          <Loader size="md" />
          <Text size="sm" c="dimmed">Loading academic procedure summary...</Text>
        </Group>
      </Container>
    );
  }

  if (error) {
    return (
      <Container size="lg" py="xl">
        <ErrorState error={error} />
      </Container>
    );
  }

  const leaves = leavesQuery.data?.results ?? [];
  const bonafides = bonafidesQuery.data?.results ?? [];
  const noDuesList = noDuesQuery.data?.results ?? [];
  const branchChanges = branchChangesQuery.data?.results ?? [];

  const isEmpty =
    leaves.length === 0 &&
    bonafides.length === 0 &&
    noDuesList.length === 0 &&
    branchChanges.length === 0;

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Other Academic Procedures"
        subtitle="Manage personal academic requests, certificates, clearances, and branch change procedures"
      />

      {isEmpty && (
        <Alert title="No active requests" color="blue" mb="lg" data-testid="empty-state">
          You have not submitted any academic procedure requests yet. Use the services below to get started.
        </Alert>
      )}

      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder padding="lg" radius="md">
            <Stack justify="space-between" h="100%">
              <div>
                <Title order={4} mb="xs">Student Leave Management</Title>
                <Text size="sm" c="dimmed" mb="md">
                  Apply for casual, medical, or semester leave. Track supervisor recommendations and HoD approval.
                </Text>
                <Text size="sm" fw={500}>
                  Active Requests: {leaves.filter((l) => l.status === "PENDING" || l.status === "RECOMMENDED").length}
                </Text>
              </div>
              <Group justify="flex-end" mt="md">
                <Button component={Link} to="leave" variant="light" size="sm">
                  Manage Leaves
                </Button>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder padding="lg" radius="md">
            <Stack justify="space-between" h="100%">
              <div>
                <Title order={4} mb="xs">Bonafide Certificate</Title>
                <Text size="sm" c="dimmed" mb="md">
                  Request official institutional bonafide certificates for passports, visas, bank loans, or internships.
                </Text>
                <Text size="sm" fw={500}>
                  Issued Certificates: {bonafides.filter((b) => b.status === "APPROVED").length}
                </Text>
              </div>
              <Group justify="flex-end" mt="md">
                <Button component={Link} to="bonafide" variant="light" size="sm">
                  View Certificates
                </Button>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder padding="lg" radius="md">
            <Stack justify="space-between" h="100%">
              <div>
                <Title order={4} mb="xs">Institutional No-Dues Clearance</Title>
                <Text size="sm" c="dimmed" mb="md">
                  Digital multi-departmental dues sign-off for graduating or departing students.
                </Text>
                <Text size="sm" fw={500}>
                  Status: {noDuesList[0]?.overall_status ?? "Not Initiated"}
                </Text>
              </div>
              <Group justify="flex-end" mt="md">
                <Button component={Link} to="no-dues" variant="light" size="sm">
                  Check No-Dues
                </Button>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <Card withBorder padding="lg" radius="md">
            <Stack justify="space-between" h="100%">
              <div>
                <Title order={4} mb="xs">Undergraduate Branch Change</Title>
                <Text size="sm" c="dimmed" mb="md">
                  Submit branch change preferences after first year. Evaluated strictly on CPI merit without backlogs.
                </Text>
                <Text size="sm" fw={500}>
                  Applications: {branchChanges.length}
                </Text>
              </div>
              <Group justify="flex-end" mt="md">
                <Button component={Link} to="branch-change" variant="light" size="sm">
                  Branch Change
                </Button>
              </Group>
            </Stack>
          </Card>
        </Grid.Col>

        {can("oap.leave.approve") && (
          <Grid.Col span={12}>
            <Card withBorder padding="lg" radius="md" style={{ borderColor: "var(--mantine-color-blue-4)" }}>
              <Group justify="space-between">
                <div>
                  <Title order={4}>Faculty & HoD Approval Queue</Title>
                  <Text size="sm" c="dimmed">
                    Review and act on pending student leave applications requiring institutional sanction.
                  </Text>
                </div>
                <Button component={Link} to="approvals" color="blue">
                  Open Approval Queue
                </Button>
              </Group>
            </Card>
          </Grid.Col>
        )}
      </Grid>
    </Container>
  );
}
