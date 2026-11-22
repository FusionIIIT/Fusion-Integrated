import React, { useEffect, useState } from "react";
import { EmployeeProfile } from "../api/types";

export const EmployeeProfilePage: React.FC = () => {
  const [profile, setProfile] = useState<EmployeeProfile | null>(null);

  useEffect(() => {
    fetch("/api/v1/hr-eis/profiles/me/")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => setProfile(data))
      .catch(() => {});
  }, []);

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <h1 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 16 }}>
        My Service Record (HR-EIS)
      </h1>
      <p style={{ color: "#666", marginBottom: 24 }}>
        Authoritative official service profile maintained under institutional governance.
      </p>
      {profile ? (
        <div style={{ background: "#fff", padding: 24, borderRadius: 8, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div><strong>Employee ID:</strong> {profile.employee_id}</div>
            <div><strong>Full Name:</strong> {profile.full_name}</div>
            <div><strong>Email:</strong> {profile.email}</div>
            <div><strong>Department:</strong> {profile.department}</div>
            <div><strong>Designation:</strong> {profile.designation}</div>
            <div><strong>Employment Type:</strong> {profile.employment_type}</div>
            <div><strong>Date of Joining:</strong> {profile.date_of_joining}</div>
            <div><strong>Status:</strong> <span style={{ color: "green", fontWeight: 600 }}>{profile.status}</span></div>
          </div>
        </div>
      ) : (
        <div>Loading official service record...</div>
      )}
    </div>
  );
};
export default EmployeeProfilePage;
