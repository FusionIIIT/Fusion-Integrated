import { useState } from "react";
import {
  Badge,
  Button,
  Card,
  Container,
  Group,
  Modal,
  NumberInput,
  Paper,
  Select,
  Stack,
  Switch,
  Tabs,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { FaIdCard, FaSlidersH, FaUserPlus } from "react-icons/fa";

import { errorMessage } from "../../../lib/http";
import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { StatusBadge } from "../../../ui/components/StatusBadge";
import {
  useCreateServiceRecord,
  useServiceRecords,
  useUpdateServiceRecord,
  useUpdateWorkflowConfig,
  useWorkflowConfigs,
} from "../api/hooks";
import type { EmployeeServiceRecord } from "../api/types";

export default function AdminSettingsPage() {
  const { data: records, isPending: recordsLoading, error: recordsError } = useServiceRecords();
  const { data: configs, error: configsError } = useWorkflowConfigs();

  const createRecord = useCreateServiceRecord();
  const updateRecord = useUpdateServiceRecord();
  const updateConfig = useUpdateWorkflowConfig();

  const [activeTab, setActiveTab] = useState<string | null>("records");

  // Record modal state
  const [recordModalOpen, setRecordModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<EmployeeServiceRecord | null>(null);
  const [userId, setUserId] = useState<number>(0);
  const [employeeId, setEmployeeId] = useState<string>("");
  const [department, setDepartment] = useState<string>("Computer Science and Engineering");
  const [designation, setDesignation] = useState<string>("Assistant Professor");
  const [category, setCategory] = useState<"faculty" | "staff">("faculty");
  const [appointmentDate, setAppointmentDate] = useState<string>("");

  // Appraisal window policy state
  const appraisalWindowConfig = configs?.find((c) => c.setting_key === "appraisal_window")?.setting_value ?? {
    active: true,
    start_date: "2026-01-01",
    end_date: "2026-12-31",
  };
  const [windowActive, setWindowActive] = useState<boolean>(Boolean(appraisalWindowConfig.active));
  const [windowStart, setWindowStart] = useState<string>(String(appraisalWindowConfig.start_date || "2026-01-01"));
  const [windowEnd, setWindowEnd] = useState<string>(String(appraisalWindowConfig.end_date || "2026-12-31"));

  if (recordsError || configsError) {
    return (
      <Container size="xl">
        <ErrorState error={recordsError || configsError} />
      </Container>
    );
  }

  const handleSaveRecord = (e: React.FormEvent) => {
    e.preventDefault();
    if (!department || !designation) {
      notifications.show({ title: "Validation Error", message: "Required fields missing", color: "red" });
      return;
    }

    if (editingRecord) {
      updateRecord.mutate(
        {
          id: editingRecord.id,
          data: {
            employee_id: employeeId,
            department,
            designation,
            category,
            appointment_date: appointmentDate || null,
          },
        },
        {
          onSuccess: () => {
            notifications.show({ title: "Updated", message: "Service record updated", color: "teal" });
            setRecordModalOpen(false);
            setEditingRecord(null);
          },
        }
      );
    } else {
      createRecord.mutate(
        {
          user_id: userId,
          employee_id: employeeId,
          department,
          designation,
          category,
          appointment_date: appointmentDate || null,
        },
        {
          onSuccess: () => {
            notifications.show({ title: "Created", message: "Service record created", color: "teal" });
            setRecordModalOpen(false);
          },
          onError: (err) => {
            notifications.show({ title: "Error", message: errorMessage(err), color: "red" });
          },
        }
      );
    }
  };

  const handleSaveAppraisalWindow = () => {
    updateConfig.mutate(
      {
        setting_key: "appraisal_window",
        setting_value: {
          active: windowActive,
          start_date: windowStart,
          end_date: windowEnd,
        },
        description: "Annual appraisal submission window and eligibility bounds",
      },
      {
        onSuccess: () => {
          notifications.show({
            title: "Policy Saved",
            message: "Appraisal submission window configuration updated.",
            color: "teal",
          });
        },
      }
    );
  };

  return (
    <Container size="xl" py="md">
      <PageHeader
        title="Human Resources System Administration"
        subtitle="Manage employee master service books, approval hierarchies, and institutional submission windows (BR-HR-004, BR-HR-034)"
      />

      <Tabs value={activeTab} onChange={setActiveTab} radius="md">
        <Tabs.List mb="lg">
          <Tabs.Tab value="records" leftSection={<FaIdCard size={14} />}>
            Employee Service Records
          </Tabs.Tab>
          <Tabs.Tab value="policies" leftSection={<FaSlidersH size={14} />}>
            Institutional Policies & Windows
          </Tabs.Tab>
        </Tabs.List>

        {/* Tab 1: Service Records */}
        <Tabs.Panel value="records">
          <Card withBorder padding="lg" radius="md">
            <Group justify="space-between" mb="md">
              <Title order={4}>Master Employee Service Books</Title>
              <Button
                leftSection={<FaUserPlus size={12} />}
                onClick={() => {
                  setEditingRecord(null);
                  setUserId(0);
                  setEmployeeId("");
                  setAppointmentDate("");
                  setRecordModalOpen(true);
                }}
                color="blue"
              >
                Create Service Record
              </Button>
            </Group>

            <DataTable<EmployeeServiceRecord>
              rows={records ?? []}
              loading={recordsLoading}
              rowKey={(r) => r.id}
              minWidth={900}
              empty={{
                icon: FaIdCard,
                title: "No employee service records",
                description: "No service records created yet in the system.",
              }}
              columns={[
                {
                  key: "user_id",
                  header: "User ID",
                  render: (r) => <Text size="sm" fw={600}>#{r.user_id}</Text>,
                },
                {
                  key: "employee_id",
                  header: "PF / Employee ID",
                  render: (r) => <Text size="sm">{r.employee_id || "PF-Auto"}</Text>,
                },
                {
                  key: "designation",
                  header: "Designation",
                  render: (r) => <Text size="sm" fw={600}>{r.designation}</Text>,
                },
                {
                  key: "department",
                  header: "Department",
                  render: (r) => <Text size="sm">{r.department}</Text>,
                },
                {
                  key: "category",
                  header: "Category",
                  render: (r) => (
                    <Badge color={r.category === "faculty" ? "blue" : "teal"} variant="light">
                      {r.category.toUpperCase()}
                    </Badge>
                  ),
                },
                {
                  key: "status",
                  header: "Status",
                  render: (r) => <StatusBadge status={r.retirement_status || "active"} />,
                },
                {
                  key: "actions",
                  header: "Action",
                  render: (r) => (
                    <Button
                      size="xs"
                      variant="subtle"
                      onClick={() => {
                        setEditingRecord(r);
                        setUserId(r.user_id);
                        setEmployeeId(r.employee_id);
                        setDepartment(r.department);
                        setDesignation(r.designation);
                        setCategory(r.category);
                        setAppointmentDate(r.appointment_date || "");
                        setRecordModalOpen(true);
                      }}
                    >
                      Edit
                    </Button>
                  ),
                },
              ]}
            />
          </Card>
        </Tabs.Panel>

        {/* Tab 2: Policies & Windows */}
        <Tabs.Panel value="policies">
          <Card withBorder padding="lg" radius="md">
            <Title order={4} mb="md">
              Annual Appraisal Submission Window (BR-HR-012)
            </Title>
            <Paper withBorder p="md" radius="sm" mb="lg">
              <Stack gap="md">
                <Switch
                  label="Enable Appraisal Form Submissions"
                  description="When disabled, faculty and staff cannot submit or modify appraisal forms."
                  checked={windowActive}
                  onChange={(e) => setWindowActive(e.currentTarget.checked)}
                />

                <Group grow>
                  <TextInput
                    label="Window Start Date"
                    type="date"
                    value={windowStart}
                    onChange={(e) => setWindowStart(e.target.value)}
                  />
                  <TextInput
                    label="Window End Date"
                    type="date"
                    value={windowEnd}
                    onChange={(e) => setWindowEnd(e.target.value)}
                  />
                </Group>

                <Group justify="flex-end">
                  <Button
                    color="teal"
                    loading={updateConfig.isPending}
                    onClick={handleSaveAppraisalWindow}
                  >
                    Save Window Policy
                  </Button>
                </Group>
              </Stack>
            </Paper>
          </Card>
        </Tabs.Panel>
      </Tabs>

      {/* Record Create/Edit Modal */}
      <Modal
        opened={recordModalOpen}
        onClose={() => setRecordModalOpen(false)}
        title={editingRecord ? "Edit Service Record" : "Create Master Employee Service Record"}
        size="md"
      >
        <form onSubmit={handleSaveRecord}>
          <Stack gap="md">
            {!editingRecord && (
              <NumberInput
                label="System User ID"
                required
                min={1}
                value={userId}
                onChange={(v) => setUserId(Number(v) || 0)}
              />
            )}

            <TextInput
              label="Permanent PF / Employee ID"
              placeholder="e.g. PF-2026-004"
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
            />

            <TextInput
              label="Department / Discipline"
              required
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            />

            <TextInput
              label="Official Designation"
              required
              value={designation}
              onChange={(e) => setDesignation(e.target.value)}
            />

            <Select
              label="Cadre / Category"
              required
              value={category}
              onChange={(v) => v && setCategory(v as "faculty" | "staff")}
              data={[
                { value: "faculty", label: "Faculty (Teaching & Research)" },
                { value: "staff", label: "Administrative / Technical Staff" },
              ]}
            />

            <TextInput
              label="Appointment Date"
              type="date"
              value={appointmentDate}
              onChange={(e) => setAppointmentDate(e.target.value)}
            />

            <Group justify="flex-end" mt="md">
              <Button variant="default" onClick={() => setRecordModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={createRecord.isPending || updateRecord.isPending} color="blue">
                Save Record
              </Button>
            </Group>
          </Stack>
        </form>
      </Modal>
    </Container>
  );
}
