import { Button, Card, Container, Stack, Text, Textarea, TextInput, Title } from "@mantine/core";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourse, useLmsDownload, useLmsList, useLmsWrite } from "../api/hooks";
import type { Announcement, Assignment, Grade, Material, Submission } from "../api/types";
import { CoursePicker, Feedback, ListState, Pending } from "../components/Common";

export default function CoursesPage() {
  const [selected, select] = useState<number | null>(null);
  return <Container size="xl"><PageHeader title="My Courses" subtitle="Course content, assignments and released feedback" />
    <Stack><CoursePicker selected={selected} onSelect={select} />
      {selected != null && <Workspace key={selected} id={selected} />}
    </Stack></Container>;
}

function Workspace({ id }: { id: number }) {
  const course = useCourse(id);
  const { can } = useAuth();
  if (course.error) return <Feedback error={course.error} />;
  if (course.isPending) return <Pending />;
  const row = course.data;
  return <Stack>
    <Card withBorder><Title order={2}>{row.course_code} · {row.course_name}</Title>
      <Title order={3}>Syllabus</Title><Text style={{ whiteSpace: "pre-wrap" }}>{row.syllabus || "Course details have not been published."}</Text>
      <Title order={3}>Schedule</Title><Text style={{ whiteSpace: "pre-wrap" }}>{row.schedule || "No schedule published."}</Text>
      <Title order={3}>Instructors and TAs</Title>
      {!row.staff.length && <Text>No staff contacts are available.</Text>}
      {row.staff.map((staff) => <Text key={`${staff.course_role}-${staff.user_id}`}>
        {staff.course_role}: {staff.display_name} {staff.email}</Text>)}
    </Card>
    <PublishedMaterials id={id} sections={row.sections} />
    <Announcements id={id} allowed={row.can_post_announcements && can("lms.announcement.create")} />
    {can("lms.assignment.view") && <StudentAssignments id={id} />}
    {can("lms.grade.view") && row.acting_course_role === "STUDENT" && <ReleasedGrades id={id} />}
  </Stack>;
}

function PublishedMaterials({ id, sections }: { id: number; sections: { id: number; label: string }[] }) {
  const query = useLmsList<Material>(`/lms/courses/${id}/materials/`);
  const download = useLmsDownload();
  return <section aria-label="Course materials"><Title order={2}>Materials</Title>
    <Feedback error={download.error} />
    <ListState pending={query.isPending} error={query.error} empty={!query.items.length}
      more={query.hasNextPage} onMore={() => void query.fetchNextPage()}>
      {[...query.items].sort((a, b) => a.order - b.order).map((item) => <Card withBorder key={item.id}>
        <Title order={3}>{item.title || `Material ${item.id}`}</Title>
        <Text>{sections.find((section) => section.id === item.section_id)?.label ?? "General"} · {item.state}</Text>
        {item.kind === "NOTE" && <Text style={{ whiteSpace: "pre-wrap" }}>{item.text}</Text>}
        {item.kind === "LINK" && <a href={item.url} target="_blank" rel="noopener noreferrer">Open material link</a>}
        {item.kind === "FILE" && <Button loading={download.isPending} onClick={() => download.mutate({
          path: `/lms/materials/${item.id}/download/`, fallback: item.file?.name ?? "material",
        })}>Download {item.file?.name ?? "material"}</Button>}
      </Card>)}
    </ListState></section>;
}

function Announcements({ id, allowed }: { id: number; allowed: boolean }) {
  const query = useLmsList<Announcement>(`/lms/courses/${id}/announcements/`);
  const write = useLmsWrite();
  const [content, setContent] = useState("");
  return <section aria-label="Course announcements"><Title order={2}>Announcements</Title>
    {allowed && <form onSubmit={(event) => { event.preventDefault(); write.mutate({
      path: `/lms/courses/${id}/announcements/`, data: { content },
    }, { onSuccess: () => setContent("") }); }}><Stack>
      <Textarea label="Announcement content" required value={content} onChange={(event) => setContent(event.currentTarget.value)} />
      <Button type="submit" loading={write.isPending}>Post announcement</Button>
    </Stack></form>}
    <Feedback error={write.error} success={write.isSuccess} />
    <ListState pending={query.isPending} error={query.error} empty={!query.items.length}
      more={query.hasNextPage} onMore={() => void query.fetchNextPage()}>
      {query.items.map((row) => <Card withBorder key={row.id}><Text style={{ whiteSpace: "pre-wrap" }}>{row.content}</Text>
        <Text size="sm">{new Date(row.created_at).toLocaleString()}</Text></Card>)}
    </ListState></section>;
}

function StudentAssignments({ id }: { id: number }) {
  const query = useLmsList<Assignment>(`/lms/courses/${id}/assignments/`);
  const [opened, open] = useState<number | null>(null);
  return <section aria-label="Course assignments"><Title order={2}>Assignments</Title>
    <ListState pending={query.isPending} error={query.error} empty={!query.items.length}
      more={query.hasNextPage} onMore={() => void query.fetchNextPage()}>
      {query.items.map((row) => <Card withBorder key={row.id}><Title order={3}>{row.title || `Assignment ${row.id}`}</Title>
        <Text>{row.state} · Due {new Date(row.due_at).toLocaleString()}</Text>
        <Button variant="light" onClick={() => open(opened === row.id ? null : row.id)}>
          {opened === row.id ? "Close assignment" : "View assignment"}</Button>
        {opened === row.id && <AssignmentWork row={row} />}
      </Card>)}
    </ListState></section>;
}

function AssignmentWork({ row }: { row: Assignment }) {
  const { can } = useAuth();
  const history = useLmsList<Submission>(can("lms.submission.view") ? `/lms/assignments/${row.id}/submissions/` : null);
  const download = useLmsDownload();
  const write = useLmsWrite();
  const [value, setValue] = useState("");
  const [file, setFile] = useState<File | null>(null);
  return <Stack>
    <Text style={{ whiteSpace: "pre-wrap" }}>{row.instructions}</Text>
    <Text>Submission type: {row.submission_type} · Points possible: {row.points_possible}</Text>
    <Button loading={download.isPending} onClick={() => download.mutate({
      path: `/lms/assignments/${row.id}/download/`, fallback: `assignment-${row.id}.txt`,
    })}>Download assignment</Button>
    <Feedback error={download.error} />
    {can("lms.submission.create") && <>
      <Title order={4}>My submission</Title>
      <ListState pending={history.isPending} error={history.error} empty={false}>
        {!history.items.length && <Text>Submission status: Missing</Text>}
        {history.items.map((item) => <Stack key={item.id}><Text>Submission status: Submitted · {new Date(item.submitted_at).toLocaleString()}</Text>
          {item.kind === "TEXT" && <Text>{item.text}</Text>}
          {item.kind === "LINK" && <a href={item.url} rel="noopener noreferrer" target="_blank">Submitted link</a>}
          {item.file && <Button onClick={() => download.mutate({ path: `/lms/submissions/${item.id}/download/`, fallback: item.file?.name ?? "submission" })}>Download submission</Button>}
        </Stack>)}
      </ListState>
      {!history.isPending && !history.error && history.items.length === 0 && <form onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(); data.set("kind", row.submission_type);
        if (row.submission_type === "FILE") { if (file) data.set("file", file); }
        else data.set(row.submission_type === "LINK" ? "url" : "text", value);
        write.mutate({ path: `/lms/assignments/${row.id}/submissions/`, data });
      }}><Stack>
        {row.submission_type === "TEXT" && <Textarea label="Submission text" required value={value} onChange={(event) => setValue(event.currentTarget.value)} />}
        {row.submission_type === "LINK" && <TextInput label="Submission link" type="url" required value={value} onChange={(event) => setValue(event.currentTarget.value)} />}
        {row.submission_type === "FILE" && <label>Submission file<input type="file" required accept=".pdf,.zip,.tar.gz,.txt,.docx,.ipynb" onChange={(event) => setFile(event.currentTarget.files?.[0] ?? null)} /></label>}
        <Text size="sm">One successful submission is allowed. File limit: 10 MB.</Text>
        <Button type="submit" loading={write.isPending}>Submit assignment</Button>
      </Stack></form>}
      <Feedback error={write.error} success={write.isSuccess} />
    </>}
  </Stack>;
}

function ReleasedGrades({ id }: { id: number }) {
  const query = useLmsList<Grade>(`/lms/courses/${id}/grades/`);
  return <section aria-label="My released grades"><Title order={2}>Released grades</Title>
    <ListState pending={query.isPending} error={query.error} empty={!query.items.length}
      more={query.hasNextPage} onMore={() => void query.fetchNextPage()}>
      {query.items.map((grade) => <Card withBorder key={grade.id}>
        <Text>Assignment {grade.assignment_id}: {grade.points} points</Text><Text>{grade.feedback}</Text>
      </Card>)}
    </ListState></section>;
}
