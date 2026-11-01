import { useState } from "react";
import {
  Button,
  Card,
  Container,
  Group,
  Modal,
  Stack,
  Tabs,
  Text,
  TextInput,
  Badge,
  NumberInput,
  Select,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaUserPlus, FaUsers, FaChalkboardTeacher } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import {
  useTAAllocations,
  useCreateTAAllocation,
  useSupervisorAllocations,
  useCreateSupervisorAllocation,
} from "../api/hooks";
import type { TAAllocation, ThesisSupervisorAllocation } from "../api/types";

export default function AllocationsPage() {
  const { data: taData, isPending: taPending, error: taError } = useTAAllocations();
  const { data: supData, isPending: supPending, error: supError } = useSupervisorAllocations();

  const createTAMutation = useCreateTAAllocation();
  const createSupMutation = useCreateSupervisorAllocation();

  const [activeTab, setActiveTab] = useState<string | null>("ta");
  const [taModalOpened, setTaModalOpened] = useState(false);
  const [supModalOpened, setSupModalOpened] = useState(false);

  // TA form states
  const [taStudentId, setTaStudentId] = useState<number | string>("");
  const [taStudentName, setTaStudentName] = useState("");
  const [taCourseCode, setTaCourseCode] = useState("");
  const [taCourseName, setTaCourseName] = useState("");
  const [taFacultyName, setTaFacultyName] = useState("");
  const [taHours, setTaHours] = useState<number>(8);

  // Supervisor form states
  const [supStudentId, setSupStudentId] = useState<number | string>("");
  const [supStudentName, setSupStudentName] = useState("");
  const [supSupervisorId, setSupSupervisorId] = useState<number | string>("");
  const [supSupervisorName, setSupSupervisorName] = useState("");
  const [supTopic, setSupTopic] = useState("");
  const [supProgramme, setSupProgramme] = useState("Ph.D.");

  if (taError || supError) {
    return <Container size="xl"><ErrorState error={taError || supError} /></Container>;
  }

  function handleCreateTA() {
    if (!taStudentId || !taStudentName || !taCourseCode || !taCourseName) {
      notifications.show({ color: "red", message: "Please fill all required TA fields." });
      return;
    }

    createTAMutation.mutate(
      {
        student_id: Number(taStudentId),
        student_name: taStudentName.trim(),
        course_code: taCourseCode.trim().toUpperCase(),
        course_name: taCourseName.trim(),
        faculty_name: taFacultyName.trim(),
        hours_per_week: taHours,
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "TA Allocated",
            message: `Allocated ${taStudentName} to ${taCourseCode}.`,
          });
          setTaModalOpened(false);
          setTaStudentId("");
          setTaStudentName("");
          setTaCourseCode("");
          setTaCourseName("");
        },
        onError: (err) => {
          notifications.show({ color: "red", message: errorMessage(err) });
        },
      }
    );
  }

  function handleCreateSupervisor() {
    if (!supStudentId || !supStudentName || !supSupervisorId || !supSupervisorName) {
      notifications.show({ color: "red", message: "Please fill all required supervisor fields." });
      return;
    }

    createSupMutation.mutate(
      {
        student_id: Number(supStudentId),
        student_name: supStudentName.trim(),
        programme: supProgramme,
        supervisor_id: Number(supSupervisorId),
        supervisor_name: supSupervisorName.trim(),
        thesis_topic: supTopic.trim(),
      },
      {
        onSuccess: () => {
          notifications.show({
            color: "green",
            title: "Supervisor Assigned",
            message: `Assigned ${supSupervisorName} as supervisor for ${supStudentName}.`,
          });
          setSupModalOpened(false);
          setSupStudentId("");
          setSupStudentName("");
          setSupSupervisorId("");
          setSupSupervisorName("");
          setSupTopic("");
        },
        onError: (err) => {
          notifications.show({ color: "red", message: errorMessage(err) });
        },
      }
    );
  }

  const taColumns = [
    {
      key: "student",
      header: "Teaching Assistant (Student)",
      render: (t: TAAllocation) => (
        <div>
          <Text fw={600} size="sm">{t.student_name}</Text>
          <Text size="xs" c="dimmed">ID: {t.student_id} ({t.programme})</Text>
        </div>
      ),
    },
    {
      key: "course",
      header: "Course & Subject",
      render: (t: TAAllocation) => (
        <div>
          <Badge variant="light" color="cyan" size="sm">{t.course_code}</Badge>
          <Text size="sm">{t.course_name}</Text>
        </div>
      ),
    },
    {
      key: "faculty",
      header: "Faculty In-Charge",
      render: (t: TAAllocation) => <Text size="sm">{t.faculty_name || "—"}</Text>,
    },
    {
      key: "hours",
      header: "Hours / Week",
      render: (t: TAAllocation) => <Text size="sm">{t.hours_per_week} hrs</Text>,
    },
  ];

  const supColumns = [
    {
      key: "scholar",
      header: "Scholar / Student",
      render: (s: ThesisSupervisorAllocation) => (
        <div>
          <Text fw={600} size="sm">{s.student_name}</Text>
          <Text size="xs" c="dimmed">ID: {s.student_id} ({s.programme})</Text>
        </div>
      ),
    },
    {
      key: "supervisor",
      header: "Assigned Thesis Supervisor",
      render: (s: ThesisSupervisorAllocation) => (
        <div>
          <Text fw={600} size="sm">{s.supervisor_name}</Text>
          {s.co_supervisor_name && (
            <Text size="xs" c="dimmed">Co-Supervisor: {s.co_supervisor_name}</Text>
          )}
        </div>
      ),
    },
    {
      key: "topic",
      header: "Thesis Research Topic",
      render: (s: ThesisSupervisorAllocation) => (
        <Text size="sm">{s.thesis_topic || "Topic TBD"}</Text>
      ),
    },
    {
      key: "session",
      header: "Academic Year",
      render: (s: ThesisSupervisorAllocation) => (
        <Badge variant="outline" size="sm">{s.academic_year}</Badge>
      ),
    },
  ];

  return (
    <Container size="xl">
      <PageHeader
        title="Departmental Allocations"
        subtitle="Manage Teaching Assistant (TA) and Thesis Supervisor assignments (AFR-OAP-043, AFR-OAP-044)"
        action={
          <Group gap="xs">
            {activeTab === "ta" ? (
              <Button
                leftSection={<FaUserPlus />}
                onClick={() => setTaModalOpened(true)}
              >
                Add TA Assignment
              </Button>
            ) : (
              <Button
                leftSection={<FaUserPlus />}
                onClick={() => setSupModalOpened(true)}
              >
                Add Supervisor Assignment
              </Button>
            )}
          </Group>
        }
      />

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List mb="md">
          <Tabs.Tab value="ta" leftSection={<FaUsers />}>
            Teaching Assistants (TA)
          </Tabs.Tab>
          <Tabs.Tab value="supervisors" leftSection={<FaChalkboardTeacher />}>
            Thesis Supervisors
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="ta">
          <Card padding="lg" withBorder>
            <DataTable<TAAllocation>
              rows={taData ?? []}
              columns={taColumns}
              loading={taPending}
              rowKey={(t) => t.id}
              empty={{
                icon: FaUsers,
                title: "No TA Allocations",
                description: "No Teaching Assistant assignments recorded for this semester.",
              }}
            />
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="supervisors">
          <Card padding="lg" withBorder>
            <DataTable<ThesisSupervisorAllocation>
              rows={supData ?? []}
              columns={supColumns}
              loading={supPending}
              rowKey={(s) => s.id}
              empty={{
                icon: FaChalkboardTeacher,
                title: "No Supervisor Allocations",
                description: "No thesis supervisor allocations recorded yet.",
              }}
            />
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* TA Modal */}
      <Modal
        opened={taModalOpened}
        onClose={() => setTaModalOpened(false)}
        title={<Text fw={700}>Record TA Assignment (AFR-OAP-044)</Text>}
      >
        <Stack gap="md">
          <Group grow>
            <TextInput
              label="Student ID"
              placeholder="e.g. 202401"
              required
              value={String(taStudentId)}
              onChange={(e) => setTaStudentId(e.currentTarget.value)}
            />
            <TextInput
              label="Student Name"
              placeholder="e.g. Rahul Verma"
              required
              value={taStudentName}
              onChange={(e) => setTaStudentName(e.currentTarget.value)}
            />
          </Group>
          <Group grow>
            <TextInput
              label="Course Code"
              placeholder="e.g. CS201"
              required
              value={taCourseCode}
              onChange={(e) => setTaCourseCode(e.currentTarget.value)}
            />
            <TextInput
              label="Course Name"
              placeholder="e.g. Data Structures"
              required
              value={taCourseName}
              onChange={(e) => setTaCourseName(e.currentTarget.value)}
            />
          </Group>
          <TextInput
            label="Faculty In-Charge"
            placeholder="e.g. Dr. A. P. Singh"
            value={taFacultyName}
            onChange={(e) => setTaFacultyName(e.currentTarget.value)}
          />
          <NumberInput
            label="Hours Per Week"
            value={taHours}
            onChange={(val) => setTaHours(Number(val) || 8)}
            min={1}
            max={20}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setTaModalOpened(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateTA} loading={createTAMutation.isPending}>
              Save Allocation
            </Button>
          </Group>
        </Stack>
      </Modal>

      {/* Supervisor Modal */}
      <Modal
        opened={supModalOpened}
        onClose={() => setSupModalOpened(false)}
        title={<Text fw={700}>Assign Thesis Supervisor (AFR-OAP-043)</Text>}
      >
        <Stack gap="md">
          <Group grow>
            <TextInput
              label="Scholar Student ID"
              placeholder="e.g. 202405"
              required
              value={String(supStudentId)}
              onChange={(e) => setSupStudentId(e.currentTarget.value)}
            />
            <TextInput
              label="Scholar Name"
              placeholder="e.g. Ananya Roy"
              required
              value={supStudentName}
              onChange={(e) => setSupStudentName(e.currentTarget.value)}
            />
          </Group>
          <Group grow>
            <TextInput
              label="Supervisor Faculty ID"
              placeholder="e.g. 301"
              required
              value={String(supSupervisorId)}
              onChange={(e) => setSupSupervisorId(e.currentTarget.value)}
            />
            <TextInput
              label="Supervisor Name"
              placeholder="e.g. Prof. M. K. Jain"
              required
              value={supSupervisorName}
              onChange={(e) => setSupSupervisorName(e.currentTarget.value)}
            />
          </Group>
          <Select
            label="Academic Programme"
            data={["Ph.D.", "M.Tech", "M.Des"]}
            value={supProgramme}
            onChange={(val: string | null) => setSupProgramme(val || "Ph.D.")}
            required
          />
          <TextInput
            label="Thesis Topic"
            placeholder="e.g. Edge Computing in Healthcare"
            value={supTopic}
            onChange={(e) => setSupTopic(e.currentTarget.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={() => setSupModalOpened(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreateSupervisor} loading={createSupMutation.isPending}>
              Save Assignment
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}
