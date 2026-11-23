import { Button, Card, Checkbox, Container, Group, NativeSelect, Stack, Text, Textarea, TextInput, Title } from "@mantine/core";
import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { PageHeader } from "../../../ui/components/PageHeader";
import { useCourse, useCoursePolicy, useUpdateCourse, useCreatePolicyVersion, useCreateSection,
  useUpdateSection, useMaterials, useCreateMaterial, useUpdateMaterial, useAssignments,
  useCreateAssignment, useUpdateAssignment } from "../api/hooks";
import type { Assignment, Course, Material, Section } from "../api/types";
import { CoursePicker, Feedback, ListState, localValue, Pending, utcValue } from "../components/Common";
import { ReleaseControls } from "../components/ReleaseControls";

export default function TeachingPage() {
  const [selected, select] = useState<number | null>(null);
  return <Container size="xl"><PageHeader title="Teaching" subtitle="Configure assigned courses and publish learning content" />
    <Stack><CoursePicker selected={selected} onSelect={select} />
      {selected != null && <TeachingWorkspace key={selected} id={selected} />}
    </Stack></Container>;
}

function TeachingWorkspace({ id }: { id: number }) {
  const course = useCourse(id);
  if (course.error) return <Feedback error={course.error} />;
  if (course.isPending) return <Pending />;
  return <Stack><Details key={`${course.data.details_published_at}-${course.data.can_post_announcements}`} course={course.data} />
    <Sections course={course.data} /><MaterialManager course={course.data} /><AssignmentManager id={id} />
  </Stack>;
}

function Details({ course }: { course: Course }) {
  const write = useUpdateCourse(course.id);
  const policy = useCreatePolicyVersion(course.id);
  const { can } = useAuth();
  const [syllabus, setSyllabus] = useState(course.syllabus);
  const [schedule, setSchedule] = useState(course.schedule);
  // Faculty's posting capability is unconditional; the versioned TA flag is read separately below.
  return <Card withBorder><Title order={2}>Course details</Title>
    {can("lms.course.update") && <form onSubmit={(event) => { event.preventDefault(); write.mutate({
      syllabus, schedule,
    }); }}><Stack>
      <Textarea label="Syllabus" value={syllabus} onChange={(event) => setSyllabus(event.currentTarget.value)} />
      <Textarea label="Schedule" value={schedule} onChange={(event) => setSchedule(event.currentTarget.value)} />
      <Button type="submit" loading={write.isPending}>Publish course details</Button>
    </Stack></form>}
    <Feedback error={write.error} success={write.isSuccess} />
    {can("lms.course_policy.update") && <PolicyForm id={course.id} write={policy} />}
  </Card>;
}

function PolicyForm({ id, write }: { id: number; write: ReturnType<typeof useCreatePolicyVersion> }) {
  const query = useCoursePolicy(id);
  if (query.error) return <Feedback error={query.error} />;
  if (query.isPending) return <Pending />;
  return <PolicyEditor key={query.data.version} write={write} initial={query.data.can_ta_post_announcements} />;
}

function PolicyEditor({ write, initial }: { write: ReturnType<typeof useCreatePolicyVersion>; initial: boolean }) {
  const [allowed, allow] = useState(initial);
  return <form onSubmit={(event) => { event.preventDefault(); write.mutate({
    can_ta_post_announcements: allowed,
  }); }}><Stack mt="md">
    <Checkbox label="Allow assigned TAs to post announcements" checked={allowed}
      onChange={(event) => allow(event.currentTarget.checked)} />
    <Button type="submit" variant="light" loading={write.isPending}>Save TA announcement policy</Button>
    <Feedback error={write.error} success={write.isSuccess} />
  </Stack></form>;
}

function Sections({ course }: { course: Course }) {
  const { can } = useAuth();
  const [editing, edit] = useState<Section | null>(null);
  return <Card withBorder><Title order={2}>Material sections</Title>
    {!course.sections.length && <Text>No sections yet.</Text>}
    {course.sections.map((section) => <Group key={section.id}>
      <Text>{section.kind}: {section.label} · Order {section.order}</Text>
      {can("lms.section.update") && <Button variant="subtle" onClick={() => edit(section)}>Edit section {section.label}</Button>}
    </Group>)}
    {(can("lms.section.create") || editing) && <SectionForm key={editing?.id ?? "new"}
      courseId={course.id} row={editing} done={() => edit(null)} />}
  </Card>;
}

function SectionForm({ courseId, row, done }: { courseId: number; row: Section | null; done: () => void }) {
  const [label, setLabel] = useState(row?.label ?? "");
  const [kind, setKind] = useState<Section["kind"]>(row?.kind ?? "MODULE");
  const [order, setOrder] = useState(row?.order ?? 0);
  const create = useCreateSection(courseId);
  const update = useUpdateSection(row?.id ?? 0);
  const write = row ? update : create;
  return <form onSubmit={(event) => { event.preventDefault(); write.mutate({
    label, kind, order,
  }, { onSuccess: () => { setLabel(""); done(); } }); }}><Stack mt="md">
    <TextInput label="Section label" required value={label} onChange={(event) => setLabel(event.currentTarget.value)} />
    <NativeSelect label="Section kind" data={["MODULE", "WEEK"]} value={kind}
      onChange={(event) => setKind(event.currentTarget.value as Section["kind"])} />
    <TextInput label="Section order" type="number" min={0} value={order}
      onChange={(event) => setOrder(Number(event.currentTarget.value))} />
    <Button type="submit" loading={write.isPending}>{row ? "Save section" : "Create section"}</Button>
    {row && <Button variant="subtle" onClick={done}>Cancel section edit</Button>}
    <Feedback error={write.error} success={write.isSuccess} />
  </Stack></form>;
}

function MaterialManager({ course }: { course: Course }) {
  const query = useMaterials(course.id);
  const { can } = useAuth();
  const [editing, edit] = useState<Material | null>(null);
  return <section aria-label="Manage materials"><Title order={2}>Manage materials</Title>
    <ListState pending={query.isPending} error={query.error} empty={!query.items.length}
      more={query.hasNextPage} onMore={() => void query.fetchNextPage()}>
      {query.items.map((row) => <Card withBorder key={row.id}><Title order={3}>{row.title || `Material ${row.id}`}</Title>
        <Text>{row.kind} · {row.state} · Order {row.order}</Text>
        {can("lms.material.update") && <Button variant="light" onClick={() => edit(row)}>Edit material {row.title || row.id}</Button>}
        <ReleaseControls kind="material" id={row.id} state={row.state} />
      </Card>)}
    </ListState>
    {(can("lms.material.create") || editing) && <MaterialForm key={editing?.id ?? "new"} course={course} row={editing} done={() => edit(null)} />}
  </section>;
}

function MaterialForm({ course, row, done }: { course: Course; row: Material | null; done: () => void }) {
  const [title, setTitle] = useState(row?.title ?? "");
  const [kind, setKind] = useState(row?.kind ?? "NOTE");
  const [text, setText] = useState(row?.text ?? "");
  const [url, setUrl] = useState(row?.url ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [section, setSection] = useState(row?.section_id ? String(row.section_id) : "");
  const [order, setOrder] = useState(row?.order ?? 0);
  const create = useCreateMaterial(course.id);
  const update = useUpdateMaterial(row?.id ?? 0);
  const write = row ? update : create;
  return <Card withBorder mt="md"><Title order={3}>{row ? "Edit material" : "New material"}</Title>
    <form onSubmit={(event) => { event.preventDefault();
      const data = new FormData(); data.set("title", title); data.set("kind", kind);
      data.set("text", kind === "NOTE" ? text : ""); data.set("url", kind === "LINK" ? url : "");
      data.set("order", String(order)); data.set("section_id", section);
      if (kind === "FILE" && file) data.set("file", file);
      write.mutate(data, { onSuccess: () => { setTitle(""); setText(""); done(); } });
    }}><Stack>
      <TextInput label="Material title" value={title} onChange={(event) => setTitle(event.currentTarget.value)} />
      <NativeSelect label="Material kind" data={["NOTE", "FILE", "LINK"]} value={kind}
        onChange={(event) => setKind(event.currentTarget.value as Material["kind"])} />
      {kind === "NOTE" && <Textarea label="Material note" required value={text} onChange={(event) => setText(event.currentTarget.value)} />}
      {kind === "LINK" && <TextInput label="Material link" type="url" required value={url} onChange={(event) => setUrl(event.currentTarget.value)} />}
      {kind === "FILE" && <label>Material file<input type="file" required={!row?.file} accept=".pdf,.zip,.tar.gz,.txt,.docx,.ipynb"
        onChange={(event) => setFile(event.currentTarget.files?.[0] ?? null)} /></label>}
      <Text size="sm">Material files: PDF, ZIP, TAR.GZ, TXT, DOCX or IPYNB. Maximum 25 MB.</Text>
      <NativeSelect label="Material section" value={section} onChange={(event) => setSection(event.currentTarget.value)}
        data={[{ value: "", label: "General" }, ...course.sections.map((item) => ({ value: String(item.id), label: item.label }))]} />
      <TextInput label="Material order" type="number" min={0} value={order} onChange={(event) => setOrder(Number(event.currentTarget.value))} />
      <Button type="submit" loading={write.isPending}>{row ? "Save material" : "Create material"}</Button>
      {row && <Button variant="subtle" onClick={done}>Cancel material edit</Button>}
      <Feedback error={write.error} success={write.isSuccess} />
    </Stack></form>
  </Card>;
}

function AssignmentManager({ id }: { id: number }) {
  const query = useAssignments(id);
  const { can } = useAuth();
  const [editing, edit] = useState<Assignment | null>(null);
  return <section aria-label="Manage assignments"><Title order={2}>Manage assignments</Title>
    <ListState pending={query.isPending} error={query.error} empty={!query.items.length}
      more={query.hasNextPage} onMore={() => void query.fetchNextPage()}>
      {query.items.map((row) => <Card withBorder key={row.id}><Title order={3}>{row.title || `Assignment ${row.id}`}</Title>
        <Text>{row.state} · {row.submission_type} · Due {new Date(row.due_at).toLocaleString()}</Text>
        {can("lms.assignment.update") && <Button variant="light" onClick={() => edit(row)}>Edit assignment {row.title || row.id}</Button>}
        <ReleaseControls kind="assignment" id={row.id} state={row.state} />
      </Card>)}
    </ListState>
    {(can("lms.assignment.create") || editing) && <AssignmentForm key={editing?.id ?? "new"} courseId={id} row={editing} done={() => edit(null)} />}
  </section>;
}

function AssignmentForm({ courseId, row, done }: { courseId: number; row: Assignment | null; done: () => void }) {
  const [title, setTitle] = useState(row?.title ?? "");
  const [instructions, setInstructions] = useState(row?.instructions ?? "");
  const [due, setDue] = useState(row ? localValue(row.due_at) : "");
  const [kind, setKind] = useState(row?.submission_type ?? "TEXT");
  const [points, setPoints] = useState(row?.points_possible ?? "0");
  const create = useCreateAssignment(courseId);
  const update = useUpdateAssignment(row?.id ?? 0);
  const write = row ? update : create;
  return <Card withBorder mt="md"><Title order={3}>{row ? "Edit assignment" : "New assignment"}</Title>
    <form onSubmit={(event) => { event.preventDefault(); write.mutate({
      title, instructions, due_at: utcValue(due), submission_type: kind, points_possible: points,
    }, { onSuccess: () => { setTitle(""); setInstructions(""); done(); } }); }}><Stack>
      <TextInput label="Assignment title (optional)" value={title} onChange={(event) => setTitle(event.currentTarget.value)} />
      <Textarea label="Assignment instructions" required value={instructions} onChange={(event) => setInstructions(event.currentTarget.value)} />
      <TextInput label="Assignment due date (local time)" type="datetime-local" required value={due} onChange={(event) => setDue(event.currentTarget.value)} />
      <NativeSelect label="Assignment submission type" data={["TEXT", "FILE", "LINK"]} value={kind}
        onChange={(event) => setKind(event.currentTarget.value as Assignment["submission_type"])} />
      <TextInput label="Points possible" type="number" step="0.01" min={0} required value={points} onChange={(event) => setPoints(event.currentTarget.value)} />
      <Button type="submit" loading={write.isPending}>{row ? "Save assignment" : "Create assignment draft"}</Button>
      {row && <Button variant="subtle" onClick={done}>Cancel assignment edit</Button>}
      <Feedback error={write.error} success={write.isSuccess} />
    </Stack></form>
  </Card>;
}
