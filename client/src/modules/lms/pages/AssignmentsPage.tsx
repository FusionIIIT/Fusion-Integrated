import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AssignmentDetailPage from "./AssignmentDetailPage";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Select,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
} from "@mantine/core";
import {
  FaCalendarAlt,
  FaCheckCircle,
  FaClipboardList,
  FaClock,
  FaSearch,
} from "react-icons/fa";

import { useAuth } from "../../../auth/AuthProvider";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import { useAllAssignments } from "../api/hooks";

export default function AssignmentsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const selectedAssignmentId = searchParams.get("assignmentId");

  const { data: assignments, isPending, error } = useAllAssignments();
  const { session } = useAuth();
  const user = session?.user;

  const [search, setSearch] = useState("");
  const [filterMode, setFilterMode] = useState<string | null>("all");

  if (selectedAssignmentId) {
    return <AssignmentDetailPage assignmentIdProp={Number(selectedAssignmentId)} />;
  }

  if (error) {
    return (
      <Container size="lg" py="md">
        <ErrorState error={error} />
      </Container>
    );
  }

  const list = assignments ?? [];
  const now = new Date();

  const filtered = list.filter((asgn) => {
    const matchesSearch =
      asgn.title.toLowerCase().includes(search.toLowerCase()) ||
      (asgn.course_code && asgn.course_code.toLowerCase().includes(search.toLowerCase()));

    const isSubmitted = !!asgn.my_submission;
    const isPastDue = new Date(asgn.due_date) < now;

    if (filterMode === "pending") {
      return matchesSearch && !isSubmitted && !isPastDue;
    }
    if (filterMode === "submitted") {
      return matchesSearch && isSubmitted;
    }
    if (filterMode === "overdue") {
      return matchesSearch && !isSubmitted && isPastDue;
    }
    return matchesSearch;
  });

  return (
    <Container size="lg" py="md">
      <PageHeader
        title="Assignments Overview"
        subtitle="Track upcoming assignment deadlines, submissions, and tasks across all courses"
      />

      <Card withBorder mb="lg" padding="md">
        <Group justify="space-between" wrap="wrap">
          <TextInput
            placeholder="Search by assignment title or course code..."
            leftSection={<FaSearch size={14} color="var(--mantine-color-gray-5)" />}
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            style={{ flex: 1, minWidth: 260 }}
          />
          <Select
            placeholder="Filter status"
            data={[
              { value: "all", label: "All Assignments" },
              { value: "pending", label: "Pending (Due soon)" },
              { value: "submitted", label: "Submitted" },
              { value: "overdue", label: "Overdue" },
            ]}
            value={filterMode}
            onChange={setFilterMode}
            style={{ width: 180 }}
          />
        </Group>
      </Card>

      {isPending && <Text c="dimmed">Loading assignments...</Text>}

      {!isPending && filtered.length === 0 && (
        <Card padding="xl" withBorder style={{ textAlign: "center" }}>
          <Stack align="center" gap="xs">
            <ThemeIcon size={46} radius="xl" color="gray" variant="light">
              <FaClipboardList size={22} />
            </ThemeIcon>
            <Text fw={600} size="md">
              No assignments found
            </Text>
            <Text c="dimmed" size="xs">
              No coursework matching your current filter criteria.
            </Text>
          </Stack>
        </Card>
      )}

      <Stack gap="sm">
        {filtered.map((asgn) => {
          const isSubmitted = !!asgn.my_submission;
          const isPastDue = new Date(asgn.due_date) < now;

          return (
            <Card
              key={asgn.id}
              withBorder
              padding="md"
              radius="md"
              style={{
                cursor: "pointer",
                transition: "box-shadow 0.15s ease",
              }}
              onClick={() => navigate(`/lms/assignments?assignmentId=${asgn.id}`)}
            >
              <Group justify="space-between" align="center" wrap="nowrap">
                <div style={{ flex: 1 }}>
                  <Group gap="xs" mb={4}>
                    <Badge color="indigo" variant="filled" size="sm">
                      {asgn.course_code}
                    </Badge>
                    <Text fw={700} size="md">
                      {asgn.title}
                    </Text>
                    <StatusBadge status={asgn.status} />
                    <Badge variant="outline" color="gray" size="xs">
                      {asgn.submission_type.toUpperCase()}
                    </Badge>
                  </Group>

                  <Group gap="md">
                    <Text size="xs" c="dimmed">
                      <FaCalendarAlt style={{ verticalAlign: "middle", marginRight: 4 }} />
                      Due: <strong>{new Date(asgn.due_date).toLocaleString()}</strong>
                    </Text>
                    <Text size="xs" c="dimmed">
                      Points: <strong>{asgn.points_possible}</strong>
                    </Text>
                  </Group>
                </div>

                <Group gap="sm">
                  {user?.kind === "student" && (
                    <div>
                      {isSubmitted ? (
                        <Badge color="green" variant="light" size="md" leftSection={<FaCheckCircle size={10} />}>
                          Submitted
                        </Badge>
                      ) : isPastDue ? (
                        <Badge color="red" variant="light" size="md" leftSection={<FaClock size={10} />}>
                          Overdue
                        </Badge>
                      ) : (
                        <Badge color="orange" variant="light" size="md">
                          Pending
                        </Badge>
                      )}
                    </div>
                  )}

                  <Button variant="subtle" size="xs" color="indigo">
                    Open &rarr;
                  </Button>
                </Group>
              </Group>
            </Card>
          );
        })}
      </Stack>
    </Container>
  );
}
