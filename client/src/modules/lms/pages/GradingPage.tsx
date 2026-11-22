import { Button, Card, Container, NativeSelect, Stack, Text, Textarea, TextInput, Title } from "@mantine/core";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourse, useLmsDownload, useLmsList, useLmsWrite } from "../api/hooks";
import type { Assignment, Grade, Submission } from "../api/types";
import { CoursePicker, Feedback, ListState, Pending } from "../components/Common";

export default function GradingPage() {
  const [selected, select] = useState<number | null>(null);
  return <Container size="xl"><PageHeader title="Grading" subtitle="Evaluate submissions and release feedback" />
    <Stack><CoursePicker selected={selected} onSelect={select} />
      {selected != null && <GradingWorkspace key={selected} id={selected} />}
    </Stack></Container>;
}

function GradingWorkspace({ id }: { id: number }) {
  const course = useCourse(id);
  const query = useLmsList<Assignment>(`/lms/courses/${id}/assignments/`);
  const [assignment, choose] = useState<number | null>(null);
  if (course.error) return <Feedback error={course.error} />;
  if (course.isPending) return <Pending />;
  return <Stack><Title order={2}>{course.data.course_name}</Title>
    <ListState pending={query.isPending} error={query.error} empty={!query.items.length}
      more={query.hasNextPage} onMore={() => void query.fetchNextPage()}>
      <NativeSelect label="Assignment to grade" value={assignment ?? ""}
        onChange={(event) => choose(event.currentTarget.value ? Number(event.currentTarget.value) : null)}
        data={[{ value: "", label: "Choose an assignment" }, ...query.items.map((row) => ({
          value: String(row.id), label: row.title || `Assignment ${row.id}`,
        }))]} />
    </ListState>
    {assignment != null && <SubmissionRows key={assignment} courseId={id} assignmentId={assignment}
      faculty={course.data.acting_course_role === "FACULTY"} />}
  </Stack>;
}

function SubmissionRows({ courseId, assignmentId, faculty }: { courseId: number; assignmentId: number; faculty: boolean }) {
  const submissions = useLmsList<Submission>(`/lms/assignments/${assignmentId}/submissions/`);
  const grades = useLmsList<Grade>(`/lms/courses/${courseId}/grades/`);
  return <Stack><Title order={2}>Student submissions</Title>
    <ListState pending={submissions.isPending || grades.isPending} error={submissions.error || grades.error}
      empty={!submissions.items.length} more={submissions.hasNextPage} onMore={() => void submissions.fetchNextPage()}>
      {submissions.items.map((row) => <Evaluation key={row.id} row={row}
        grade={grades.items.find((grade) => grade.submission_id === row.id)} faculty={faculty} />)}
    </ListState>
    {grades.hasNextPage && <Button onClick={() => void grades.fetchNextPage()} loading={grades.isFetchingNextPage}>Load more grades</Button>}
  </Stack>;
}

function Evaluation({ row, grade, faculty }: { row: Submission; grade?: Grade; faculty: boolean }) {
  const { can } = useAuth();
  const download = useLmsDownload();
  return <Card withBorder><Stack>
    <Title order={3}>Submission {row.id} · User {row.user_id}</Title>
    <Text>Submitted {new Date(row.submitted_at).toLocaleString()}</Text>
    {row.kind === "TEXT" && <Text style={{ whiteSpace: "pre-wrap" }}>{row.text}</Text>}
    {row.kind === "LINK" && <a href={row.url} target="_blank" rel="noopener noreferrer">Open submitted link</a>}
    {row.file && <Button loading={download.isPending} onClick={() => download.mutate({
      path: `/lms/submissions/${row.id}/download/`, fallback: row.file?.name ?? "submission",
    })}>Download submission {row.id}</Button>}
    <Feedback error={download.error} />
    {grade && <Text>Grade {grade.state}: {grade.points} · {grade.feedback}</Text>}
    {can(grade ? "lms.grade.update" : "lms.grade.create") && (grade?.state !== "RELEASED" || faculty)
      && <GradeForm key={`${grade?.id}-${grade?.points}-${grade?.feedback}`} row={row} grade={grade} />}
    {grade?.state === "DRAFT" && can("lms.grade.publish") && faculty && <ReleaseGrade id={row.id} />}
  </Stack></Card>;
}

function GradeForm({ row, grade }: { row: Submission; grade?: Grade }) {
  const write = useLmsWrite();
  const [points, setPoints] = useState(grade?.points ?? "");
  const [feedback, setFeedback] = useState(grade?.feedback ?? "");
  return <form onSubmit={(event) => { event.preventDefault(); write.mutate({
    path: `/lms/submissions/${row.id}/grade/`, method: grade ? "patch" : "post", data: { points, feedback },
  }); }}><Stack>
    <TextInput label={`Points for submission ${row.id}`} type="number" step="0.01" min={0} required value={points}
      onChange={(event) => setPoints(event.currentTarget.value)} />
    <Textarea label={`Feedback for submission ${row.id}`} value={feedback}
      onChange={(event) => setFeedback(event.currentTarget.value)} />
    <Button type="submit" loading={write.isPending}>{grade?.state === "RELEASED" ? "Correct released grade" : "Save draft grade"}</Button>
    <Feedback error={write.error} success={write.isSuccess} />
  </Stack></form>;
}

function ReleaseGrade({ id }: { id: number }) {
  const write = useLmsWrite();
  return <Stack><Button loading={write.isPending} onClick={() => write.mutate({
    path: `/lms/submissions/${id}/grade/release/`,
  })}>Release grade for submission {id}</Button><Feedback error={write.error} success={write.isSuccess} /></Stack>;
}
