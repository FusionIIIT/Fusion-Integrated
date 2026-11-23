import { useApplications } from "../api/hooks";

export default function MyApplicationsPage() {
  const { data: applications, isLoading, error } = useApplications();

  if (isLoading) {
    return <div role="status">Loading your applications...</div>;
  }

  if (error) {
    return <div role="alert">Failed to load applications. Please try again.</div>;
  }

  if (!applications || applications.length === 0) {
    return <div>You have not submitted any applications yet.</div>;
  }

  return (
    <div>
      <h1>My Applications</h1>
      <table>
        <thead>
          <tr>
            <th>Application ID</th>
            <th>Cycle</th>
            <th>Status</th>
            <th>Submitted At</th>
          </tr>
        </thead>
        <tbody>
          {applications.map((app) => (
            <tr key={app.id}>
              <td>{app.application_id}</td>
              <td>{app.academic_cycle}</td>
              <td>{app.state}</td>
              <td>{app.submitted_at ?? "Draft"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
