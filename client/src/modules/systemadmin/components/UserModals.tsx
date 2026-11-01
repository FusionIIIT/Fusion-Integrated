import { useState } from "react";
import {
  Modal,
  TextInput,
  Select,
  NumberInput,
  Stack,
  Button,
  Group,
  Textarea,
  Text,
  Alert,
} from "@mantine/core";
import { useCreateUser, useUpdateUser, useChangeUserStatus, useBulkCreateUsers } from "../api/hooks";
import type { BasicUser } from "../api/types";
import { errorMessage } from "../../../lib/http";

export function CreateUserModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const [userType, setUserType] = useState<string>("student");
  const [instituteId, setInstituteId] = useState("");
  const [fullName, setFullName] = useState("");
  const [instituteEmail, setInstituteEmail] = useState("");
  const [dateOfJoining, setDateOfJoining] = useState(new Date().toISOString().split("T")[0]);
  const [department, setDepartment] = useState("Computer Science and Engineering");
  const [programme, setProgramme] = useState("B.Tech");
  const [discipline, setDiscipline] = useState("CSE");
  const [batchYear, setBatchYear] = useState<number | string>(2024);
  const [employeeId, setEmployeeId] = useState("");
  const [contactNumber, setContactNumber] = useState("");
  const [error, setError] = useState<string | null>(null);

  const createMutation = useCreateUser();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await createMutation.mutateAsync({
        institute_id: instituteId,
        user_type: userType,
        full_name: fullName,
        institute_email: instituteEmail,
        date_of_joining: dateOfJoining,
        department,
        programme: userType === "student" ? programme : "",
        discipline: userType === "student" ? discipline : "",
        batch_year: userType === "student" ? Number(batchYear) : null,
        employee_id: userType !== "student" ? employeeId : "",
        contact_number: contactNumber,
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Create Basic User Account" size="lg">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Select
            label="User Type"
            data={[
              { value: "student", label: "Student" },
              { value: "faculty", label: "Faculty" },
              { value: "staff", label: "Staff" },
            ]}
            value={userType}
            onChange={(val) => setUserType(val ?? "student")}
            required
          />
          <Group grow>
            <TextInput
              label="Institute ID / Roll No"
              placeholder="e.g. 2024CS001 or FAC001"
              value={instituteId}
              onChange={(e) => setInstituteId(e.target.value)}
              required
            />
            <TextInput
              label="Full Name"
              placeholder="Dr. / Mr. / Ms. Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </Group>
          <Group grow>
            <TextInput
              label="Institute Email"
              placeholder="name@iiitdmj.ac.in"
              value={instituteEmail}
              onChange={(e) => setInstituteEmail(e.target.value)}
              required
            />
            <TextInput
              label="Date of Joining"
              type="date"
              value={dateOfJoining}
              onChange={(e) => setDateOfJoining(e.target.value)}
              required
            />
          </Group>
          <TextInput
            label="Department"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            required
          />
          {userType === "student" && (
            <Group grow>
              <TextInput
                label="Programme"
                placeholder="B.Tech / M.Tech / Ph.D"
                value={programme}
                onChange={(e) => setProgramme(e.target.value)}
                required
              />
              <TextInput
                label="Discipline"
                placeholder="CSE / ECE / ME / Design"
                value={discipline}
                onChange={(e) => setDiscipline(e.target.value)}
              />
              <NumberInput
                label="Batch Year"
                value={batchYear}
                onChange={(val) => setBatchYear(val)}
                required
              />
            </Group>
          )}
          {userType !== "student" && (
            <TextInput
              label="Employee ID"
              placeholder="EMP-..."
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              required
            />
          )}
          <TextInput
            label="Contact Number"
            placeholder="+91-..."
            value={contactNumber}
            onChange={(e) => setContactNumber(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={createMutation.isPending}>Create User</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function EditUserModal({
  user,
  opened,
  onClose,
}: {
  user: BasicUser;
  opened: boolean;
  onClose: () => void;
}) {
  const [fullName, setFullName] = useState(user.full_name);
  const [contactNumber, setContactNumber] = useState(user.contact_number);
  const [department, setDepartment] = useState(user.department);
  const [programme, setProgramme] = useState(user.programme);
  const [discipline, setDiscipline] = useState(user.discipline);
  const [error, setError] = useState<string | null>(null);

  const updateMutation = useUpdateUser(user.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await updateMutation.mutateAsync({
        full_name: fullName,
        contact_number: contactNumber,
        department,
        programme: user.user_type === "student" ? programme : "",
        discipline: user.user_type === "student" ? discipline : "",
      });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title={`Edit Profile: ${user.institute_id}`} size="md">
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <TextInput label="Institute ID (Immutable)" value={user.institute_id} disabled />
          <TextInput label="Institute Email (Immutable)" value={user.institute_email} disabled />
          <TextInput
            label="Full Name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
          <TextInput
            label="Department"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            required
          />
          {user.user_type === "student" && (
            <Group grow>
              <TextInput
                label="Programme"
                value={programme}
                onChange={(e) => setProgramme(e.target.value)}
              />
              <TextInput
                label="Discipline"
                value={discipline}
                onChange={(e) => setDiscipline(e.target.value)}
              />
            </Group>
          )}
          <TextInput
            label="Contact Number"
            value={contactNumber}
            onChange={(e) => setContactNumber(e.target.value)}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={updateMutation.isPending}>Save Changes</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function ChangeStatusModal({
  user,
  action,
  opened,
  onClose,
}: {
  user: BasicUser;
  action: "deactivate" | "reactivate";
  opened: boolean;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const statusMutation = useChangeUserStatus(user.id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await statusMutation.mutateAsync({ action, reason });
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={`${action === "deactivate" ? "Deactivate" : "Reactivate"} Account: ${user.institute_id}`}
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          <Text size="sm">
            Are you sure you want to {action} account for <b>{user.full_name}</b> ({user.institute_id})?
          </Text>
          <Textarea
            label="Reason (Mandatory for audit trail)"
            placeholder="Provide justification..."
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
            minRows={3}
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Cancel</Button>
            <Button
              type="submit"
              color={action === "deactivate" ? "red" : "green"}
              loading={statusMutation.isPending}
            >
              Confirm {action === "deactivate" ? "Deactivation" : "Reactivation"}
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}

export function BulkCreateModal({ opened, onClose }: { opened: boolean; onClose: () => void }) {
  const [csvText, setCsvText] = useState("");
  const [result, setResult] = useState<{ success: number; failure: number } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const bulkMutation = useBulkCreateUsers();

  const handleParseAndSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    const lines = csvText.trim().split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length < 2) {
      setError("Please provide a CSV header and at least one record row.");
      return;
    }

    const firstLine = lines[0];
    if (!firstLine) {
      setError("Please provide a CSV header and at least one record row.");
      return;
    }
    const headers = firstLine.split(",").map((h) => h.trim());
    const records = [];

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      if (!line) continue;
      const parts = line.split(",").map((p) => p.trim());
      const rec: Record<string, unknown> = {};
      headers.forEach((h, idx) => {
        rec[h] = parts[idx] ?? "";
      });
      records.push(rec);
    }

    try {
      const res = await bulkMutation.mutateAsync({ users: records });
      setResult({ success: res.success_count, failure: res.failure_count });
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Bulk User Import (CSV)" size="lg">
      <form onSubmit={handleParseAndSubmit}>
        <Stack gap="sm">
          {error && <Alert color="red">{error}</Alert>}
          {result && (
            <Alert color={result.failure === 0 ? "green" : "orange"}>
              Import Finished: {result.success} succeeded, {result.failure} failed.
            </Alert>
          )}
          <Text size="xs" c="dimmed">
            Format: institute_id,user_type,full_name,institute_email,date_of_joining,department,programme,batch_year,employee_id
          </Text>
          <Textarea
            label="CSV Data (up to 1000 records)"
            placeholder={`institute_id,user_type,full_name,institute_email,date_of_joining,department,programme,batch_year,employee_id\n2024CS801,student,Rohan Sharma,rohan.2024cs801@iiitdmj.ac.in,2024-08-01,CSE,B.Tech,2024,\nFAC801,faculty,Dr. Kavita Rao,kavita@iiitdmj.ac.in,2022-01-01,ECE,,,EMP-ECE-801`}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            minRows={10}
            required
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={onClose}>Close</Button>
            <Button type="submit" loading={bulkMutation.isPending}>Import Records</Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
