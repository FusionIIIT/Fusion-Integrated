import React, { useEffect, useState } from "react";
import { getRebates, submitRebate } from "../api";
import type { RebateRequest } from "../types";

export const RebatesPage: React.FC = () => {
  const [rebates, setRebates] = useState<RebateRequest[]>([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [messName, setMessName] = useState("Central Mess");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");

  const loadRebates = () => {
    getRebates().then(setRebates).catch(console.error);
  };

  useEffect(() => {
    loadRebates();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await submitRebate({
        mess_name: messName,
        start_date: startDate,
        end_date: endDate,
        reason,
      });
      setMessage("Rebate requested successfully! (Minimum 3 days)");
      loadRebates();
    } catch (err: any) {
      setMessage("Failed to submit rebate. Check minimum 3 days and 1-day advance notice.");
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>Mess Rebates</h2>
      {message && <div style={{ padding: "10px", marginBottom: "10px", background: "#fef3c7" }}>{message}</div>}

      <form onSubmit={handleSubmit} style={{ marginBottom: "30px", maxWidth: "400px" }}>
        <h3>Apply for Meal Rebate</h3>
        <div style={{ marginBottom: "10px" }}>
          <label>Start Date: </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{ width: "100%", padding: "6px" }}
            required
          />
        </div>
        <div style={{ marginBottom: "10px" }}>
          <label>End Date: </label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={{ width: "100%", padding: "6px" }}
            required
          />
        </div>
        <div style={{ marginBottom: "10px" }}>
          <label>Reason: </label>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            style={{ width: "100%", padding: "6px" }}
          />
        </div>
        <button type="submit" style={{ padding: "8px 16px" }}>Submit Rebate</button>
      </form>

      <h3>My Rebate Requests</h3>
      {rebates.length === 0 ? (
        <p>No rebate requests found.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "8px" }}>ID</th>
              <th style={{ padding: "8px" }}>Duration</th>
              <th style={{ padding: "8px" }}>Dates</th>
              <th style={{ padding: "8px" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {rebates.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "8px" }}>#{r.id}</td>
                <td style={{ padding: "8px" }}>{r.duration_days} days</td>
                <td style={{ padding: "8px" }}>{r.start_date} to {r.end_date}</td>
                <td style={{ padding: "8px" }}>{r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default RebatesPage;

