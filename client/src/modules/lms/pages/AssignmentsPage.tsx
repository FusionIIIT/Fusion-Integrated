import { useParams } from "react-router-dom";

import { useAssignments } from "../api/hooks";

export default function AssignmentsPage() {
  const { id } = useParams<{ id: string }>();
  const courseId = Number(id);
  const { data, isLoading, isError, error } = useAssignments(courseId);

  if (isLoading) return <div>Loading assignments…</div>;
  if (isError) return <div>Failed to load assignments: {String(error)}</div>;
  if (!data || data.length === 0) return <div>No assignments yet.</div>;

  return (
    <ul>
      {data.map((a) => (
        <li key={a.id}>{a.title} — due {a.due_at} ({a.status})</li>
      ))}
    </ul>
  );
}