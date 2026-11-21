import { useState } from "react";
import {
  NumberInput,
  Select,
  Stack,
  TextInput,
  PasswordInput,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";

import { errorMessage } from "../../../lib/http";
import { FormModal } from "../../../ui/components/FormModal";
import { FormRow, FormSection } from "../../../ui/components/FormSection";
import { useCreateUser } from "../api/hooks";
import type { UserKind } from "../api/types";

const USER_KINDS = [
  { value: "student", label: "Student" },
  { value: "faculty", label: "Faculty" },
  { value: "staff", label: "Staff" },
];

export function CreateUserModal({
  opened,
  onClose,
}: {
  opened: boolean;
  onClose: () => void;
}) {
  const createUser = useCreateUser();

  const [kind, setKind] = useState<UserKind>("student");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [instituteId, setInstituteId] = useState("");
  const [contactNumber, setContactNumber] = useState("");
  const [department, setDepartment] = useState("");
  const [programme, setProgramme] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [batchYear, setBatchYear] = useState<number | string>(
    new Date().getFullYear(),
  );
  const [employeeId, setEmployeeId] = useState("");
  const [initialPassword, setInitialPassword] = useState("");

  const resetForm = () => {
    setName("");
    setEmail("");
    setInstituteId("");
    setContactNumber("");
    setDepartment("");
    setProgramme("");
    setDiscipline("");
    setBatchYear(new Date().getFullYear());
    setEmployeeId("");
    setInitialPassword("");
  };

  const handleSubmit = () => {
    if (!name.trim() || !email.trim() || !instituteId.trim()) {
      notifications.show({
        color: "red",
        title: "Required Fields Missing",
        message: "Name, email, and Institute ID are required.",
      });
      return;
    }

    createUser.mutate(
      {
        user_kind: kind,
        name: name.trim(),
        institute_email: email.trim(),
        institute_id: instituteId.trim(),
        contact_number: contactNumber.trim() || undefined,
        department: department.trim() || undefined,
        programme: kind === "student" ? programme.trim() || undefined : undefined,
        discipline: discipline.trim() || undefined,
        batch_year:
          kind === "student" && batchYear ? Number(batchYear) : undefined,
        employee_id:
          kind !== "student" ? employeeId.trim() || undefined : undefined,
        initial_password: initialPassword.trim() || undefined,
      },
      {
        onSuccess: (data) => {
          notifications.show({
            color: "green",
            title: "User Created",
            message: `Account for ${data.username} (${data.institute_id}) created successfully.`,
          });
          resetForm();
          onClose();
        },
        onError: (err) => {
          notifications.show({
            color: "red",
            title: "Creation Failed",
            message: errorMessage(err),
          });
        },
      },
    );
  };

  return (
    <FormModal
      opened={opened}
      onClose={onClose}
      title="Create New User Account"
      subtitle="Onboard a new student, faculty member, or staff account"
      onSubmit={handleSubmit}
      submitting={createUser.isPending}
      submitLabel="Create User"
      size="lg"
    >
      <Stack gap="md">
        <FormSection title="Account Identity">
          <FormRow>
            <Select
              label="User Classification"
              data={USER_KINDS}
              value={kind}
              onChange={(v) => setKind((v as UserKind) || "student")}
              required
            />
            <TextInput
              label={kind === "student" ? "Roll Number / ID" : "Institute ID"}
              placeholder={kind === "student" ? "e.g. 21BCS045" : "e.g. FAC012"}
              value={instituteId}
              onChange={(e) => setInstituteId(e.currentTarget.value)}
              required
            />
          </FormRow>

          <FormRow>
            <TextInput
              label="Full Name"
              placeholder="e.g. Priya Sharma"
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
              required
            />
            <TextInput
              label="Institute Email"
              placeholder="e.g. priya.s@iiitdmj.ac.in"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              required
            />
          </FormRow>
        </FormSection>

        <FormSection title="Academic / Departmental Placement">
          <FormRow>
            <TextInput
              label="Department"
              placeholder="e.g. Computer Science & Engineering"
              value={department}
              onChange={(e) => setDepartment(e.currentTarget.value)}
            />
            <TextInput
              label="Discipline"
              placeholder="e.g. CSE"
              value={discipline}
              onChange={(e) => setDiscipline(e.currentTarget.value)}
            />
          </FormRow>

          {kind === "student" ? (
            <FormRow>
              <TextInput
                label="Programme"
                placeholder="e.g. B.Tech / M.Tech / Ph.D."
                value={programme}
                onChange={(e) => setProgramme(e.currentTarget.value)}
              />
              <NumberInput
                label="Batch Year"
                value={batchYear}
                onChange={(v) => setBatchYear(v)}
                min={2005}
                max={2035}
              />
            </FormRow>
          ) : (
            <FormRow>
              <TextInput
                label="Employee ID"
                placeholder="e.g. EMP-2024-001"
                value={employeeId}
                onChange={(e) => setEmployeeId(e.currentTarget.value)}
              />
              <TextInput
                label="Contact Number"
                placeholder="e.g. +91 9876543210"
                value={contactNumber}
                onChange={(e) => setContactNumber(e.currentTarget.value)}
              />
            </FormRow>
          )}
        </FormSection>

        <FormSection title="Authentication">
          <PasswordInput
            label="Initial Password"
            description="Leave blank to generate an onboarding invitation with temporary credentials"
            placeholder="Min 8 characters with complexity"
            value={initialPassword}
            onChange={(e) => setInitialPassword(e.currentTarget.value)}
          />
        </FormSection>
      </Stack>
    </FormModal>
  );
}
