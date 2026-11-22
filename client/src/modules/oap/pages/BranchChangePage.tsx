import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Container,
  Group,
  Loader,
  Select,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { useAuth } from "../../../auth/AuthProvider";
import { errorMessage } from "../../../lib/http";
import { ErrorState } from "../../../ui/components/ErrorState";
import { FormModal } from "../../../ui/components/FormModal";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useBranchChanges, useSubmitBranchChange } from "../api/hooks";

const BRANCHES = [
  { value: "CSE", label: "Computer Science and Engineering" },
  { value: "ECE", label: "Electronics and Communication Engineering" },
  { value: "ME", label: "Mechanical Engineering" },
  { value: "SM", label: "Smart Manufacturing" },
  { value: "DES", label: "Design" },
];

export default function BranchChangePage() {
  const { data, isPending, error } = useBranchChanges();
  const { can, session } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);

  const [studentId, setStudentId] = useState(session?.user.username ?? "");
  const [currentBranch, setCurrentBranch] = useState("ECE");
  const [pref1, setPref1] = useState("CSE");
  const [pref2, setPref2] = useState("SM");
  const [cpi, setCpi] = useState("8.50");
  const [credits, setCredits] = useState("40");
  const [hasBacklogs, setHasBacklogs] = useState(false);

  const submitMutation = useSubmitBranchChange();
  const canApply = can("oap.branchchange.apply");

  if (isPending) {
    return (
      <Container size="lg" py="xl">
        <Group justify="center" p="xl" data-testid="loading-state">
          <Loader size="md" />
          <Text size="sm" c="dimmed">Loading branch change application status...</Text>
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

  const applications = data?.results ?? [];
  const currentApp = applications.length > 0 ? applications[0] : null;

  const handleApply = async () => {
    try {
      await submitMutation.mutateAsync({
        student_id: studentId,
        current_branch: currentBranch,
        preferred_branch_1: pref1,
        preferred_branch_2: pref2 || undefined,
        current_cpi: cpi,
        credits_completed: parseInt(credits, 10) || 0,
        has_backlogs: hasBacklogs,
      });
      notifications.show({
        color: "green",
        title: "Application Submitted",
        message: "Your branch change request has been recorded for institutional merit evaluation.",
      });
      setModalOpen(false);
    } catch (e) {
      notifications.show({
        color: "red",
        title: "Application Refused",
        message: errorMessage(e),
      });
    }
  };

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Undergraduate Branch Change"
        subtitle="Apply for change of branch based on first-year academic performance and CPI merit"
        action={
          !currentApp &&
          canApply && (
            <Button onClick={() => setModalOpen(true)} data-testid="apply-branch-change-btn">
              Apply for Branch Change
            </Button>
          )
        }
      />

      {!currentApp ? (
        <Alert title="No branch change application" color="blue" data-testid="empty-state">
          You have not submitted a branch change application. Click &quot;Apply for Branch Change&quot; above to submit your preferences.
        </Alert>
      ) : (
        <Card withBorder padding="lg" radius="md">
          <Group justify="space-between" mb="md">
            <div>
              <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                Application #{currentApp.id}
              </Text>
              <Title order={3}>
                {currentApp.current_branch} → {currentApp.preferred_branch_1}
              </Title>
              {currentApp.preferred_branch_2 && (
                <Text size="sm" c="dimmed">
                  Second Preference: {currentApp.preferred_branch_2}
                </Text>
              )}
            </div>
            <Badge
              size="xl"
              color={
                currentApp.status === "APPROVED"
                  ? "green"
                  : currentApp.status === "INELIGIBLE" || currentApp.status === "REJECTED"
                    ? "red"
                    : currentApp.status === "ALLOCATED"
                      ? "teal"
                      : "blue"
              }
            >
              {currentApp.status.replace(/_/g, " ")}
            </Badge>
          </Group>

          <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md" mt="lg">
            <Card withBorder padding="sm">
              <Text size="xs" c="dimmed">Current CPI</Text>
              <Text size="lg" fw={700}>{currentApp.current_cpi}</Text>
            </Card>
            <Card withBorder padding="sm">
              <Text size="xs" c="dimmed">Earned Credits</Text>
              <Text size="lg" fw={700}>{currentApp.credits_completed}</Text>
            </Card>
            <Card withBorder padding="sm">
              <Text size="xs" c="dimmed">Active Backlogs</Text>
              <Text size="lg" fw={700} c={currentApp.has_backlogs ? "red" : "green"}>
                {currentApp.has_backlogs ? "Yes" : "None"}
              </Text>
            </Card>
          </SimpleGrid>

          {currentApp.allocated_branch && (
            <Alert color="green" mt="lg" title="Seat Allocation Confirmed">
              <Text size="sm">
                Congratulations! You have been allocated a seat in <strong>{currentApp.allocated_branch}</strong>.
              </Text>
            </Alert>
          )}

          {currentApp.remarks && (
            <Text size="sm" c="dimmed" mt="md">
              Remarks: {currentApp.remarks}
            </Text>
          )}
        </Card>
      )}

      <FormModal
        opened={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Apply for Undergraduate Branch Change"
        submitLabel="Submit Application"
        onSubmit={handleApply}
        submitting={submitMutation.isPending}
      >
        <Stack gap="md">
          <TextInput
            label="Student ID"
            value={studentId}
            onChange={(e) => setStudentId(e.currentTarget.value)}
            required
            aria-label="Student ID"
          />
          <Select
            label="Current Branch"
            data={BRANCHES}
            value={currentBranch}
            onChange={(val) => setCurrentBranch(val ?? "ECE")}
            required
            aria-label="Current Branch"
          />
          <Select
            label="1st Preferred Branch"
            data={BRANCHES}
            value={pref1}
            onChange={(val) => setPref1(val ?? "CSE")}
            required
            aria-label="1st Preferred Branch"
          />
          <Select
            label="2nd Preferred Branch (Optional)"
            data={BRANCHES}
            value={pref2}
            onChange={(val) => setPref2(val ?? "")}
            clearable
            aria-label="2nd Preferred Branch"
          />
          <Group grow>
            <TextInput
              label="Current CPI (Min 8.00)"
              value={cpi}
              onChange={(e) => setCpi(e.currentTarget.value)}
              required
              aria-label="Current CPI"
            />
            <TextInput
              label="Credits Completed (Min 36)"
              type="number"
              value={credits}
              onChange={(e) => setCredits(e.currentTarget.value)}
              required
              aria-label="Credits Completed"
            />
          </Group>
          <Checkbox
            label="I currently have active academic backlog(s)"
            checked={hasBacklogs}
            onChange={(e) => setHasBacklogs(e.currentTarget.checked)}
            aria-label="Backlog Checkbox"
          />
        </Stack>
      </FormModal>
    </Container>
  );
}
