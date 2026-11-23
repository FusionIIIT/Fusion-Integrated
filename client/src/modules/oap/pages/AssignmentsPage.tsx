import { useState } from "react";
import { Button, Card, Container, Group, NumberInput, Stack, TextInput } from "@mantine/core";

import { DataTable } from "../../../ui/components/DataTable";
import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { notifyDone, notifyError } from "../components/notify";
import {
  useRecordTA, useRecordThesis, useTAAssignments, useThesisAssignments,
} from "../api/hooks";
import type { TAAssignment, ThesisAssignment } from "../api/types";

export default function AssignmentsPage() {
  const thesis = useThesisAssignments();
  const ta = useTAAssignments();
  const recordThesis = useRecordThesis();
  const recordTA = useRecordTA();
  const [student, setStudent] = useState<number | string>("");
  const [supervisor, setSupervisor] = useState<number | string>("");
  const [course, setCourse] = useState("");

  const thesisCols = [
    { key: "student", header: "Student", render: (r: ThesisAssignment) => r.student_user_id },
    { key: "sup", header: "Supervisor", render: (r: ThesisAssignment) => r.supervisor_user_id },
    { key: "at", header: "Recorded", render: (r: ThesisAssignment) => new Date(r.assigned_at).toLocaleDateString() },
  ];
  const taCols = [
    { key: "student", header: "Student", render: (r: TAAssignment) => r.student_user_id },
    { key: "course", header: "Course", render: (r: TAAssignment) => r.course_code || "—" },
    { key: "sup", header: "Faculty", render: (r: TAAssignment) => r.supervisor_user_id ?? "—" },
  ];

  return (
    <Container size="lg" py="md">
      <PageHeader title="Supervisor and TA assignments" subtitle="Record the departmental decisions." />
      <Card withBorder mb="md">
        <Stack gap="sm">
          <Group grow align="flex-end">
            <NumberInput label="Student user id" value={student} onChange={setStudent} min={1} />
            <NumberInput label="Supervisor user id" value={supervisor} onChange={setSupervisor} min={1} />
          </Group>
          <Group justify="flex-end">
            <Button loading={recordThesis.isPending} disabled={!student || !supervisor}
              onClick={() => recordThesis.mutate({ student_user_id: Number(student), supervisor_user_id: Number(supervisor) }, {
                onSuccess: () => notifyDone("Thesis supervisor recorded."), onError: notifyError })}>Record thesis supervisor</Button>
          </Group>
          <Group grow align="flex-end">
            <TextInput label="Course or subject (optional)" value={course} onChange={(e) => setCourse(e.currentTarget.value)} />
          </Group>
          <Group justify="flex-end">
            <Button variant="light" loading={recordTA.isPending} disabled={!student || (!course && !supervisor)}
              onClick={() => recordTA.mutate({ student_user_id: Number(student), course_code: course,
                supervisor_user_id: supervisor ? Number(supervisor) : null }, {
                onSuccess: () => notifyDone("TA assignment recorded."), onError: notifyError })}>Record TA assignment</Button>
          </Group>
        </Stack>
      </Card>
      {thesis.error ? <ErrorState error={thesis.error} /> : (
        <DataTable rows={thesis.data ?? []} columns={thesisCols} loading={thesis.isPending} minWidth={560}
          rowKey={(r) => r.id} empty={{ title: "No thesis supervisors recorded." }} />
      )}
      {ta.error ? <ErrorState error={ta.error} /> : (
        <DataTable rows={ta.data ?? []} columns={taCols} loading={ta.isPending} minWidth={560}
          rowKey={(r) => r.id} empty={{ title: "No TA assignments recorded." }} />
      )}
    </Container>
  );
}
