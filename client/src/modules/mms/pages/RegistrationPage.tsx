import React, { useEffect, useState } from "react";
import { getRegistrationWindows, getStudentRegistrations, submitRegistration } from "../api";
import type { MessRegistration, RegistrationWindow } from "../types";

export const RegistrationPage: React.FC = () => {
  const [windows, setWindows] = useState<RegistrationWindow[]>([]);
  const [registrations, setRegistrations] = useState<MessRegistration[]>([]);
  const [selectedWindow, setSelectedWindow] = useState<number | "">("");
  const [messName, setMessName] = useState("Central Mess");
  const [message, setMessage] = useState("");

  const loadData = () => {
    getRegistrationWindows().then(setWindows).catch(console.error);
    getStudentRegistrations().then(setRegistrations).catch(console.error);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWindow) return;
    try {
      await submitRegistration(Number(selectedWindow), messName);
      setMessage("Registration submitted successfully!");
      loadData();
    } catch (err: any) {
      setMessage("Error submitting registration.");
    }
  };

  return (
    <div style={{ padding: "20px" }}>
      <h2>Mess Registration</h2>
      {message && <div style={{ padding: "10px", marginBottom: "10px", background: "#f0fdf4" }}>{message}</div>}

      <form onSubmit={handleSubmit} style={{ marginBottom: "30px", maxWidth: "400px" }}>
        <h3>New Registration</h3>
        <div style={{ marginBottom: "10px" }}>
          <label>Registration Window: </label>
          <select
            value={selectedWindow}
            onChange={(e) => setSelectedWindow(Number(e.target.value))}
            style={{ width: "100%", padding: "6px" }}
            required
          >
            <option value="">Select an open semester window</option>
            {windows.map((w) => (
              <option key={w.id} value={w.id}>
                {w.semester} ({w.start_date} to {w.end_date})
              </option>
            ))}
          </select>
        </div>
        <div style={{ marginBottom: "10px" }}>
          <label>Mess Name: </label>
          <input
            type="text"
            value={messName}
            onChange={(e) => setMessName(e.target.value)}
            style={{ width: "100%", padding: "6px" }}
            required
          />
        </div>
        <button type="submit" style={{ padding: "8px 16px" }}>Register</button>
      </form>

      <h3>My Registrations</h3>
      {registrations.length === 0 ? (
        <p>No registrations found.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}>
              <th style={{ padding: "8px" }}>ID</th>
              <th style={{ padding: "8px" }}>Mess</th>
              <th style={{ padding: "8px" }}>Date</th>
              <th style={{ padding: "8px" }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {registrations.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid #eee" }}>
                <td style={{ padding: "8px" }}>#{r.id}</td>
                <td style={{ padding: "8px" }}>{r.mess_name}</td>
                <td style={{ padding: "8px" }}>{r.registered_date}</td>
                <td style={{ padding: "8px" }}>{r.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default RegistrationPage;

