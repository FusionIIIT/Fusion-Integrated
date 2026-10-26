import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { getApplication } from "../api/api";
import type { LeaveApplication } from "../api/types";

export const LeavePrintPage = () => {
  const { applicationId } = useParams();
  const [application, setApplication] = useState<LeaveApplication | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!applicationId || !/^\d+$/.test(applicationId)) {
      setError("Invalid application number.");
      setLoading(false);
      return;
    }
    getApplication(Number(applicationId))
      .then(setApplication)
      .catch((cause: unknown) => setError(errorMessage(cause)))
      .finally(() => setLoading(false));
  }, [applicationId]);

  if (loading) return <p>Loading application…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (!application) return <p>Application not found.</p>;

  return (
    <main className="leave-print-page">
      <h2>Leave Application</h2>
      <dl>
        <dt>Application number</dt><dd>{application.id}</dd>
        <dt>Leave type</dt>
        <dd>{application.leave_category_code}: {application.leave_category_label}</dd>
        <dt>Period</dt><dd>{application.requested_start} to {application.requested_end}</dd>
        <dt>Purpose</dt><dd>{application.purpose}</dd>
        <dt>Status</dt><dd>{application.status.replaceAll("_", " ")}</dd>
        {application.station_leave && (
          <><dt>Station Leave details</dt><dd>{application.station_leave_details}</dd></>
        )}
      </dl>
      <button type="button" onClick={() => window.print()}>Print application</button>
    </main>
  );
};
