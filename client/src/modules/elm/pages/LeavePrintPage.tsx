import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { LeaveApplication } from "../api/types";

export const LeavePrintPage = () => {
  const { applicationId } = useParams();
  const [application, setApplication] = useState<LeaveApplication | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a full implementation, this would fetch the application by ID
    // For now, simulate with placeholder data
    setApplication({
      id: Number(applicationId),
      user_id: 1,
      leave_category: { code: "EL", label: "Earned Leave" },
      requested_start: new Date(),
      requested_end: new Date(),
      purpose: "Annual leave",
      status: "sanctioned",
      created_at: new Date(),
    });
    setLoading(false);
  }, [applicationId]);

  if (loading) {
    return <div>Loading application...</div>;
  }

  if (!application) {
    return <div>Application not found.</div>;
  }

  return (
    <div className="leave-print-page">
      <h2>Leave Application Print</h2>
      <div className="application-details">
        <p><strong>Employee ID:</strong> {application.user_id}</p>
        <p><strong>Leave Type:</strong> {application.leave_category.code}</p>
        <p><strong>Purpose:</strong> {application.purpose}</p>
        <p><strong>Period:</strong> {application.requested_start.toLocaleDateString()}
          - {application.requested_end.toLocaleDateString()}</p>
        <p><strong>Status:</strong> {application.status}</p>
      </div>
      <button className="btn-print" onClick="window.print()">Print Application</button>
    </div>
  );
};