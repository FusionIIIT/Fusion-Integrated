import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import {
  Button, Card, Group, NumberInput, Select, Stack, Tabs,
  Text, TextInput, Textarea,
} from "@mantine/core";
import { useParams } from "react-router-dom";

import { ErrorState } from "../../../ui/components/ErrorState";
import { PageHeader } from "../../../ui/components/PageHeader";
import { http, errorMessage } from "../../../lib/http";
import { submissionStatus } from "../submissionStatus";

type Row = Record<string, any>;
interface Course extends Row {
  source_course_id: string;
  code: string;
  title: string;
  role: string;
  syllabus: string;
  schedule: string;
  may_announce: boolean;
  may_grade: boolean;
}

export default function CoursePage() {
  const { courseId = "" } = useParams();
  const [course, setCourse] = useState<Course>();
  const [sections, setSections] = useState<Row[]>([]);
  const [materials, setMaterials] = useState<Row[]>([]);
  const [announcements, setAnnouncements] = useState<Row[]>([]);
  const [assignments, setAssignments] = useState<Row[]>([]);
  const [submissions, setSubmissions] = useState<Row[]>([]);
  const [grades, setGrades] = useState<Row[]>([]);
  const [error, setError] = useState<unknown>();
  const [notice, setNotice] = useState("");
  const base = `/lms/courses/${encodeURIComponent(courseId)}`;

  const refresh = useCallback(async () => {
    const c = await http.get(base);
    const current: Course = c.data;
    setCourse(current);
    const requests = [
      http.get(`${base}/sections`), http.get(`${base}/materials`),
      http.get(`${base}/announcements`),
      current.role === "student" || current.role === "faculty"
        ? http.get(`${base}/assignments`) : Promise.resolve({ data: { results: [] } }),
      ["student", "faculty", "teaching_assistant"].includes(current.role)
        ? http.get(`${base}/submissions`) : Promise.resolve({ data: { results: [] } }),
      current.role === "student" || current.role === "faculty" ||
        (current.role === "teaching_assistant" && current.may_grade)
        ? http.get(`${base}/grades`) : Promise.resolve({ data: { results: [] } }),
    ];
    const [s, m, a, as, sub, g] = await Promise.all(requests);
    setSections(s.data.results ?? []);
    setMaterials(m.data.results ?? []);
    setAnnouncements(a.data.results ?? []);
    setAssignments(as.data.results ?? []);
    setSubmissions(sub.data.results ?? []);
    setGrades(g.data.results ?? []);
  }, [base]);

  useEffect(() => {
    refresh().catch(setError);
  }, [refresh]);

  async function mutate(action: () => Promise<unknown>) {
    setNotice("");
    try {
      await action();
      await refresh();
      setNotice("Saved.");
    } catch (e) {
      setNotice(errorMessage(e));
    }
  }

  function submit(handler: (form: FormData) => Promise<unknown>) {
    return (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const data = new FormData(event.currentTarget);
      void mutate(() => handler(data));
      event.currentTarget.reset();
    };
  }

  if (error) return <ErrorState error={error} />;
  if (!course) return <Text c="dimmed">Loading course…</Text>;

  const faculty = course.role === "faculty";
  const grader = faculty || course.role === "teaching_assistant" && course.may_grade;
  const student = course.role === "student";
  const canAnnounce = faculty || course.role === "teaching_assistant" && course.may_announce;

  return (
    <Stack>
      <PageHeader title={`${course.code} · ${course.title}`} subtitle={`Course role: ${course.role}`} />
      {notice && <Text role="status">{notice}</Text>}
      <Tabs defaultValue="home">
        <Tabs.List>
          <Tabs.Tab value="home">Course home</Tabs.Tab>
          <Tabs.Tab value="materials">Materials</Tabs.Tab>
          <Tabs.Tab value="announcements">Announcements</Tabs.Tab>
          {(faculty || student) && <Tabs.Tab value="assignments">Assignments</Tabs.Tab>}
          {(student || faculty || course.role === "teaching_assistant") &&
            <Tabs.Tab value="submissions">Submissions</Tabs.Tab>}
          {(student || grader) && <Tabs.Tab value="grades">Grades</Tabs.Tab>}
        </Tabs.List>

        <Tabs.Panel value="home" pt="md">
          <Card withBorder padding="lg">
            <Stack>
              {faculty ? (
                <form onSubmit={submit((form) => http.patch(`${base}/details`, {
                  syllabus: form.get("syllabus"), schedule: form.get("schedule"),
                }))}>
                  <Stack>
                    <Textarea label="Syllabus" name="syllabus" defaultValue={course.syllabus} />
                    <Textarea label="Schedule" name="schedule" defaultValue={course.schedule} />
                    <Button type="submit">Save course details</Button>
                  </Stack>
                </form>
              ) : (
                <>
                  <Text fw={600}>Syllabus</Text><Text>{course.syllabus || "Not provided."}</Text>
                  <Text fw={600}>Schedule</Text><Text>{course.schedule || "Not provided."}</Text>
                </>
              )}
              <Text fw={600}>Instructor(s)</Text>
              <Text>{course.instructors.map((p: Row) => p.display_name).join(", ") || "—"}</Text>
              <Text fw={600}>TA(s)</Text>
              <Text>{course.teaching_assistants.map((p: Row) => p.display_name).join(", ") || "—"}</Text>
            </Stack>
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="materials" pt="md">
          <Stack>
            {faculty && <Card withBorder padding="lg"><form onSubmit={submit((form) => {
              const body = new FormData();
              for (const [key, value] of form.entries()) {
                if (value !== "") body.append(key, value);
              }
              return http.post(`${base}/materials`, body);
            })}><Stack>
              <TextInput label="Title" name="title" required />
              <Select label="Type" name="kind" data={["file", "link", "note"]} required />
              <Select label="Section" name="section" data={sections.map((s) => ({
                value: String(s.id), label: `${s.kind}: ${s.title}`,
              }))} clearable />
              <Textarea label="Note" name="note" />
              <TextInput label="Link" name="link" />
              <Text size="sm">File</Text><input type="file" name="file" />
              <TextInput label="Release date/time" name="release_at" type="datetime-local" />
              <Button type="submit">Add material</Button>
            </Stack></form></Card>}
            {faculty && <Card withBorder padding="lg"><form onSubmit={submit((form) =>
              http.post(`${base}/sections`, {
                kind: form.get("kind"), title: form.get("title"),
                sort_order: Number(form.get("sort_order") || 0),
              }))}><Group align="end">
              <Select label="Section type" name="kind" data={["module", "week"]} required />
              <TextInput label="Section name" name="title" required />
              <NumberInput label="Order" name="sort_order" min={0} defaultValue={0} />
              <Button type="submit">Add section</Button>
            </Group></form></Card>}
            {sections.map((section) => <Text key={section.id} fw={600}>
              {section.kind}: {section.title}
            </Text>)}
            {materials.map((item) => <Card key={item.id} withBorder padding="md">
              <Text fw={600}>{item.title}</Text><Text size="sm">{item.status}</Text>
              {item.kind === "note" && <Text>{item.note}</Text>}
              {item.kind === "link" && <a href={item.link}>{item.link}</a>}
              {item.kind === "file" && <Button component="a"
                href={`/api/v1${base}/materials/${item.id}/download`}>Download</Button>}
            </Card>)}
            {!materials.length && <Text c="dimmed">No published materials.</Text>}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="announcements" pt="md">
          <Stack>
            {canAnnounce &&
              <Card withBorder padding="lg"><form onSubmit={submit((form) =>
                http.post(`${base}/announcements`, {
                  title: form.get("title"), content: form.get("content"),
                }))}><Stack>
                <TextInput label="Title" name="title" required />
                <Textarea label="Announcement" name="content" required />
                <Button type="submit">Post announcement</Button>
              </Stack></form></Card>}
            {announcements.map((item) => <Card key={item.id} withBorder padding="md">
              <Text fw={600}>{item.title}</Text><Text size="xs" c="dimmed">
                {new Date(item.published_at).toLocaleString()}
              </Text><Text>{item.content}</Text>
            </Card>)}
            {!announcements.length && <Text c="dimmed">No announcements.</Text>}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="assignments" pt="md">
          <Stack>
            {faculty && <Card withBorder padding="lg"><form onSubmit={submit((form) => {
              const body = new FormData();
              body.set("title", String(form.get("title")));
              body.set("due_at", new Date(String(form.get("due_at"))).toISOString());
              body.set("instructions", String(form.get("instructions")));
              body.set("submission_type", String(form.get("submission_type")));
              body.set("points_possible", String(form.get("points_possible")));
              const releaseAt = form.get("release_at");
              if (releaseAt) body.set("release_at", new Date(String(releaseAt)).toISOString());
              const file = form.get("file");
              if (file instanceof File && file.size) body.set("file", file);
              return http.post(`${base}/assignments`, body);
            })}><Stack>
              <TextInput label="Title" name="title" required />
              <Textarea label="Instructions" name="instructions" required />
              <Select label="Submission type" name="submission_type"
                data={["file", "text", "link"]} required />
              <NumberInput label="Points possible" name="points_possible" min={0} required />
              <TextInput label="Due date/time" name="due_at" type="datetime-local" required />
              <TextInput label="Release date/time (leave blank for immediate)"
                name="release_at" type="datetime-local" />
              <Text size="sm">Optional assignment file</Text><input type="file" name="file" />
              <Button type="submit">Save draft assignment</Button>
            </Stack></form></Card>}
            {assignments.map((item) => <Card key={item.id} withBorder padding="md">
              <Stack>
                <Text fw={600}>{item.title}</Text><Text>{item.instructions}</Text>
                <Text size="sm">Due {new Date(item.due_at).toLocaleString()} · {item.status}</Text>
                {item.download_url && <Button component="a"
                  href={item.download_url}>
                  Download assignment file
                </Button>}
                {student && <Text size="sm" role="status">
                  Submission status: {submissionStatus(
                    item.due_at,
                    submissions.find((row) => row.assignment === item.id),
                  ) ?? "not submitted"}
                </Text>}
                {faculty && item.status === "draft" && <Button onClick={() => void mutate(() =>
                  http.post(`${base}/assignments/${item.id}/publish`))}>Publish</Button>}
                {student && !submissions.some((row) => row.assignment === item.id) &&
                  Date.now() < new Date(item.due_at).getTime() && <form onSubmit={submit((form) => {
                  const body = new FormData();
                  for (const [key, value] of form.entries()) body.append(key, value);
                  body.set("content_type", item.submission_type);
                  return http.post(`${base}/assignments/${item.id}/submit`, body);
                })}><Stack>
                  {item.submission_type === "file" && <>
                    <Text size="sm">Submission file</Text><input type="file" name="file" required />
                  </>}
                  {item.submission_type === "text" && <Textarea label="Submission" name="text" required />}
                  {item.submission_type === "link" && <TextInput label="Submission link" name="link" required />}
                  <Button type="submit">Submit work</Button>
                </Stack></form>}
              </Stack>
            </Card>)}
            {!assignments.length && <Text c="dimmed">No assignments available.</Text>}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="submissions" pt="md">
          <Stack>{submissions.map((item) => <Card key={item.id} withBorder padding="md">
            <Text fw={600}>{item.assignment_title}</Text>
            <Text size="sm">Submitted {new Date(item.submitted_at).toLocaleString()}</Text>
            {item.text && <Text>{item.text}</Text>}
            {item.link && <a href={item.link}>{item.link}</a>}
            {item.download_url && <Button component="a" href={item.download_url}>
              Download submission
            </Button>}
            {grader && <form onSubmit={submit((form) => http.post(
              `${base}/submissions/${item.id}/grade`, {
                points: form.get("points"), feedback: form.get("feedback"),
              }))}><Group align="end">
              <NumberInput label="Points" name="points" min={0} required />
              <TextInput label="Feedback" name="feedback" />
              <Button type="submit">Save grade</Button>
            </Group></form>}
          </Card>)}</Stack>
        </Tabs.Panel>

        <Tabs.Panel value="grades" pt="md">
          <Stack>{faculty && <Card withBorder padding="lg">
            <Text size="sm">Draft grades can be released one or more at a time.</Text>
            {grades.filter((g) => g.status === "draft").map((g) => <label key={g.id}>
              <input type="checkbox" name="grade_ids" value={g.id} />
              {g.assignment_title}: {g.points}
            </label>)}
            <Button onClick={(event) => {
              const card = event.currentTarget.closest(".mantine-Card-root");
              const grade_ids = Array.from(card?.querySelectorAll<HTMLInputElement>(
                'input[name="grade_ids"]:checked') ?? []).map((input) => Number(input.value));
              void mutate(() => http.post(`${base}/grades`, { grade_ids }));
            }}>Release selected grades</Button>
          </Card>}
          {grades.map((grade) => <Card key={grade.id} withBorder padding="md">
            <Text fw={600}>{grade.assignment_title}: {grade.points}</Text>
            <Text>{grade.feedback}</Text><Text size="sm">{grade.status}</Text>
          </Card>)}</Stack>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
