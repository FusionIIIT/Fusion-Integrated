import { useParams } from "react-router-dom";

import { useCourseWorkspace } from "../api/hooks";

export default function CoursePage() {
  const { id } = useParams<{ id: string }>();
  const courseId = Number(id);
  const { data, isLoading, isError, error } = useCourseWorkspace(courseId);

  if (isLoading) return <div>Loading course…</div>;
  if (isError) return <div>Failed to load course: {String(error)}</div>;
  if (!data) return <div>No course found.</div>;

  return (
    <div>
      <h1>Course {data.course_id}</h1>
      <p>{data.title}</p>
    </div>
  );
}