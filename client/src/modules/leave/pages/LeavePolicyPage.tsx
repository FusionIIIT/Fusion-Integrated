import { useState } from "react";
import { Button, Card, Container, Group, Modal, Select, Stack, TextInput } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { DataTable } from "../../../ui/components/DataTable";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useLeavePolicies, useCreateLeavePolicy, useUpdateLeavePolicy } from "../hooks/useLeaveRequests";
import type { LeaveCategory, EmployeeType, LeavePolicy } from "../api/types";

const CATEGORIES: { value: LeaveCategory; label: string }[] = [
  { value: "CL", label: "Casual Leave (CL)" },
  { value: "RH", label: "Restricted Holiday (RH)" },
  { value: "SCL", label: "Special Casual Leave (SCL)" },
  { value: "EL", label: "Earned Leave (EL)" },
  { value: "VL", label: "Vacation Leave (VL)" },
  { value: "COL", label: "Commuted Leave (COL)" },
];

const EMPLOYEE_TYPES: { value: EmployeeType; label: string }[] = [
  { value: "faculty", label: "Faculty" },
  { value: "non_faculty", label: "Non-Faculty" },
];

export default function LeavePolicyPage() {
  const notify = notifications;
  const { data, isPending, refetch } = useLeavePolicies();
  const policies = data ?? { results: [] };
  const createPolicy = useCreateLeavePolicy();
  const updatePolicy = useUpdateLeavePolicy();

  const [modalOpen, setModalOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<LeavePolicy | null>(null);
  const [formData, setFormData] = useState({
    category: "CL" as LeaveCategory,
    employee_type: "non_faculty" as EmployeeType,
    annual_entitlement: "",
    carries_forward: false,
    half_day_allowed: false,
    requires_medical_certificate: false,
    max_per_request: "",
    effective_from: new Date().toISOString().split("T")[0],
    effective_to: "",
    is_active: true,
  });

  const handleOpenCreate = () => {
    setEditingPolicy(null);
    setFormData({
      category: "CL",
      employee_type: "non_faculty",
      annual_entitlement: "",
      carries_forward: false,
      half_day_allowed: false,
      requires_medical_certificate: false,
      max_per_request: "",
      effective_from: new Date().toISOString().split("T")[0],
      effective_to: "",
      is_active: true,
    });
    setModalOpen(true);
  };

  const handleOpenEdit = (policy: LeavePolicy) => {
    setEditingPolicy(policy);
    setFormData({
      category: policy.category,
      employee_type: policy.employee_type,
      annual_entitlement: policy.annual_entitlement,
      carries_forward: policy.carries_forward,
      half_day_allowed: policy.half_day_allowed,
      requires_medical_certificate: policy.requires_medical_certificate,
      max_per_request: policy.max_per_request || "",
      effective_from: policy.effective_from,
      effective_to: policy.effective_to || "",
      is_active: policy.is_active,
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (editingPolicy) {
        await updatePolicy.mutateAsync({ id: editingPolicy.id, body: formData });
      } else {
        await createPolicy.mutateAsync(formData);
      }
      notify.show({ title: "Success", message: editingPolicy ? "Policy updated" : "Policy created", color: "green" });
      setModalOpen(false);
      refetch();
    } catch {
      notify.show({ title: "Error", message: "Failed to save policy", color: "red" });
    }
  };

  return (
    <Container size="xl">
      <PageHeader title="Leave Policy" subtitle="Manage leave policy parameters" action={<Button onClick={handleOpenCreate}>Add Policy</Button>} />
      <Card padding="lg">
        <DataTable
          rows={policies.results}
          loading={isPending}
          minWidth={1000}
          rowKey={(row) => row.id}
          columns={[
            { key: "category", header: "Category" },
            { key: "employee_type", header: "Employee Type" },
            { key: "annual_entitlement", header: "Annual Entitlement" },
            { key: "carries_forward", header: "Carries Forward", render: (r) => r.carries_forward ? "Yes" : "No" },
            { key: "half_day_allowed", header: "Half Day Allowed", render: (r) => r.half_day_allowed ? "Yes" : "No" },
            { key: "requires_medical_certificate", header: "Medical Cert Required", render: (r) => r.requires_medical_certificate ? "Yes" : "No" },
            { key: "max_per_request", header: "Max Per Request" },
            { key: "effective_from", header: "Effective From" },
            { key: "effective_to", header: "Effective To" },
            { key: "is_active", header: "Active", render: (r) => r.is_active ? "Yes" : "No" },
            {
              key: "actions",
              header: "Actions",
              render: (r) => (
                <Group>
                  <Button variant="subtle" size="sm" onClick={() => handleOpenEdit(r)}>Edit</Button>
                </Group>
              ),
            },
          ]}
          empty={{ title: "No policies", description: "Create your first leave policy." }}
        />
      </Card>

      <Modal opened={modalOpen} onClose={() => setModalOpen(false)} title={editingPolicy ? "Edit Policy" : "Create Policy"}>
        <Stack gap="md">
          <Select
            label="Category *"
            placeholder="Select category"
            value={formData.category}
            onChange={(v) => setFormData((p) => ({ ...p, category: v as LeaveCategory }))}
            data={CATEGORIES}
            required
          />
          <Select
            label="Employee Type *"
            placeholder="Select employee type"
            value={formData.employee_type}
            onChange={(v) => setFormData((p) => ({ ...p, employee_type: v as EmployeeType }))}
            data={EMPLOYEE_TYPES}
            required
          />
          <TextInput
            label="Annual Entitlement *"
            type="number"
            value={formData.annual_entitlement}
            onChange={(e) => setFormData((p) => ({ ...p, annual_entitlement: e.currentTarget.value }))}
            required
          />
          <TextInput
            label="Max Per Request"
            type="number"
            value={formData.max_per_request}
            onChange={(e) => setFormData((p) => ({ ...p, max_per_request: e.currentTarget.value }))}
          />
          <input
            type="date"
            value={formData.effective_from}
            onChange={(e) => setFormData((p) => ({ ...p, effective_from: e.currentTarget.value }))}
            className="mantine-Input-input"
            style={{ width: "100%" }}
          />
          <input
            type="date"
            value={formData.effective_to}
            onChange={(e) => setFormData((p) => ({ ...p, effective_to: e.currentTarget.value }))}
            className="mantine-Input-input"
            style={{ width: "100%" }}
          />
          <Group>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={formData.carries_forward}
                onChange={(e) => setFormData((p) => ({ ...p, carries_forward: e.currentTarget.checked }))}
              />
              Carries Forward
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={formData.half_day_allowed}
                onChange={(e) => setFormData((p) => ({ ...p, half_day_allowed: e.currentTarget.checked }))}
              />
              Half Day Allowed
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={formData.requires_medical_certificate}
                onChange={(e) => setFormData((p) => ({ ...p, requires_medical_certificate: e.currentTarget.checked }))}
              />
              Requires Medical Certificate
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData((p) => ({ ...p, is_active: e.currentTarget.checked }))}
              />
              Active
            </label>
          </Group>
          <Group>
            <Button onClick={handleSubmit} loading={createPolicy.isPending || updatePolicy.isPending}>
              Save
            </Button>
            <Button variant="subtle" onClick={() => setModalOpen(false)}>Cancel</Button>
          </Group>
        </Stack>
      </Modal>
    </Container>
  );
}