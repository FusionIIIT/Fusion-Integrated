import { useParams } from "react-router-dom";

import { useMaterials } from "../api/hooks";

export default function MaterialsPage() {
  const { id } = useParams<{ id: string }>();
  const courseId = Number(id);
  const { data, isLoading, isError, error } = useMaterials(courseId);

  if (isLoading) return <div>Loading materials…</div>;
  if (isError) return <div>Failed to load materials: {String(error)}</div>;
  if (!data || data.length === 0) return <div>No materials published yet.</div>;

  return (
    <ul>
      {data.map((m) => (
        <li key={m.id}>{m.title} ({m.material_type})</li>
      ))}
    </ul>
  );
}