import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { LeaveApplication } from "../api/types";
import { getPendingApplications } from "../api/selectors";

export const LeaveApplicationsPage = () => {
  const { userId } = useParams();
  const [applications, setApplications] = useState<LeaveApplication[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (userId) {
      const apps = getPendingApplications(userId);
      setApplications(apps);
    }
    setLoading(false);
  }, [userId]);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="leave-applications-page">
      <h2>Leave Applications</h2>
      {applications.length === 0 ? (
        <p>No pending leave applications.</p>
      ) : (
        <ul>
          {applications.map((app) => (
            <li key={app.id}>
              <strong>{app.leave_category.code}</strong>
              {app.requested_start} - {app.requested_end}
              <br />
              Status: {app.status}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};