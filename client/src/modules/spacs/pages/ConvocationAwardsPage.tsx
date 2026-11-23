import { useAwards } from "../api/hooks";

export default function ConvocationAwardsPage() {
  const { data: awards, isLoading, error } = useAwards();

  if (isLoading) {
    return <div role="status">Loading convocation awards...</div>;
  }

  if (error) {
    return <div role="alert">Failed to load convocation awards. Please try again.</div>;
  }

  if (!awards || awards.length === 0) {
    return <div>No convocation awards published yet.</div>;
  }

  return (
    <div>
      <h1>Convocation Awards & Medals</h1>
      <table>
        <thead>
          <tr>
            <th>Student ID</th>
            <th>CPI</th>
            <th>Standing</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {awards.map((cand) => (
            <tr key={cand.id}>
              <td>{cand.student_user_id}</td>
              <td>{cand.cpi}</td>
              <td>{cand.academic_standing}</td>
              <td>{cand.shortlisted ? "Shortlisted / Awarded" : "Nominated"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
