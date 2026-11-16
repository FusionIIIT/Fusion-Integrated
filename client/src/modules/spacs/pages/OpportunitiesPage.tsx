import { useSchemes } from "../api/hooks";

export default function OpportunitiesPage() {
  const { data: schemes, isLoading, error } = useSchemes();

  if (isLoading) {
    return <div role="status">Loading scholarship and award opportunities...</div>;
  }

  if (error) {
    return <div role="alert">Failed to load opportunities. Please try again.</div>;
  }

  if (!schemes || schemes.length === 0) {
    return <div>No active scholarship opportunities available at this time.</div>;
  }

  return (
    <div>
      <h1>Scholarship and Award Opportunities</h1>
      <ul>
        {schemes.map((s) => (
          <li key={s.id}>
            <h3>{s.name}</h3>
            <p>{s.description}</p>
            <span>Min CPI: {s.min_cpi}</span>
            <button aria-label={`Apply for ${s.name}`}>Apply Now</button>
          </li>
        ))}
      </ul>
    </div>
  );
}
