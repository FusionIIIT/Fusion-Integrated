import React from "react";
import { Link } from "react-router-dom";

export const MessDashboardPage: React.FC = () => {
  return (
    <div style={{ padding: "24px" }}>
      <h1>Mess Management System</h1>
      <p style={{ color: "#666" }}>
        Welcome to the central hostel dining and mess management portal.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px", marginTop: "24px" }}>
        <div style={{ padding: "16px", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
          <h3>Weekly Menu</h3>
          <p>Check the daily breakfast, lunch, and dinner menu for all mess halls.</p>
          <Link to="/mms/menu" style={{ color: "#2563eb", textDecoration: "underline" }}>View Menu →</Link>
        </div>

        <div style={{ padding: "16px", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
          <h3>Registration</h3>
          <p>Register for a mess facility during an open registration window.</p>
          <Link to="/mms/registration" style={{ color: "#2563eb", textDecoration: "underline" }}>Register Now →</Link>
        </div>

        <div style={{ padding: "16px", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
          <h3>Meal Rebates</h3>
          <p>Apply for rebates when away from campus for 3 or more consecutive days.</p>
          <Link to="/mms/rebates" style={{ color: "#2563eb", textDecoration: "underline" }}>Apply Rebate →</Link>
        </div>
      </div>
    </div>
  );
};

export default MessDashboardPage;

