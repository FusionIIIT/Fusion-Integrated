import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { LeaveApplication } from "../api/types";
import { getApprovedLeaveYears } from "../api/selectors";

export const LeaveHistoryPage = () => {
  const { userId } = useParams();
  const [years, setYears] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (userId) {
      const yearsData = getApprovedLeaveYears(userId);
      setYears(yearsData.map((y: any) => y.year));
    }
    setLoading(false);
  }, [userId]);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="leave-history-page">
      <h2>Leave History</h2>
      {years.length === 0 ? (
        <p>No approved leave found.</p>
      ) : (
        <ul>
          {years.map((year) => (
            <li key={year}>{year} leave records</li>
          ))}
        </ul>
      )}
    </div>
  );
};