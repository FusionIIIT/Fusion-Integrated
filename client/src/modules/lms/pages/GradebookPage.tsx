import { useParams } from "react-router-dom";

export default function GradebookPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div>
      <h1>Gradebook — Course {id}</h1>
      <p>Grades will appear here once released.</p>
    </div>
  );
}