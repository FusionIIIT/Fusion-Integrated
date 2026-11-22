import { useParams } from "react-router-dom";

import { useAnnouncements } from "../api/hooks";

export default function AnnouncementsPage() {
  const { id } = useParams<{ id: string }>();
  const courseId = Number(id);
  const { data, isLoading, isError, error } = useAnnouncements(courseId);

  if (isLoading) return <div>Loading announcements…</div>;
  if (isError) return <div>Failed to load announcements: {String(error)}</div>;
  if (!data || data.length === 0) return <div>No announcements yet.</div>;

  return (
    <ul>
      {data.map((a) => (
        <li key={a.id}>{a.content} — {a.created_at}</li>
      ))}
    </ul>
  );
}