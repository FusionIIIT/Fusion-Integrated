import React, { useState } from "react";

const ClubManagement = () => {
  const [activeTab, setActiveTab] = useState<"leadership" | "booking" | "budget">("leadership");

  return (
    <div style={{ padding: "1.5rem" }}>
      <h2>Club Coordinator Management</h2>
      <div style={{ display: "flex", gap: "1rem", margin: "1rem 0" }}>
        <button
          onClick={() => setActiveTab("leadership")}
          style={{ padding: "8px 16px", background: activeTab === "leadership" ? "#2563eb" : "#f1f5f9", color: activeTab === "leadership" ? "#fff" : "#1e293b", border: "none", borderRadius: "4px" }}
        >
          Leadership Succession
        </button>
        <button
          onClick={() => setActiveTab("booking")}
          style={{ padding: "8px 16px", background: activeTab === "booking" ? "#2563eb" : "#f1f5f9", color: activeTab === "booking" ? "#fff" : "#1e293b", border: "none", borderRadius: "4px" }}
        >
          Venue Bookings
        </button>
        <button
          onClick={() => setActiveTab("budget")}
          style={{ padding: "8px 16px", background: activeTab === "budget" ? "#2563eb" : "#f1f5f9", color: activeTab === "budget" ? "#fff" : "#1e293b", border: "none", borderRadius: "4px" }}
        >
          Budget Requests
        </button>
      </div>

      <div style={{ border: "1px solid #e2e8f0", padding: "1.5rem", borderRadius: "8px" }}>
        {activeTab === "leadership" && <p>Manage active coordinator and co-coordinator succession for your club.</p>}
        {activeTab === "booking" && <p>Schedule sessions and events in configured campus venues without timing conflicts.</p>}
        {activeTab === "budget" && <p>Submit club operational budget requests with required supporting estimates.</p>}
      </div>
    </div>
  );
};

export default ClubManagement;
