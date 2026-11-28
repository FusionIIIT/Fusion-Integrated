import React, { useState } from "react";
import { leaveApi } from "../api/leaveApi";

export default function ApplyLeavePage() {
  const [category, setCategory] = useState<string>("CL");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [halfDayType, setHalfDayType] = useState<string>("NONE");
  const [purpose, setPurpose] = useState<string>("");
  
  // Station leave fields
  const [isStationLeave, setIsStationLeave] = useState<boolean>(false);
  const [stationAddress, setStationAddress] = useState<string>("");
  const [outStart, setOutStart] = useState<string>("");
  const [outEnd, setOutEnd] = useState<string>("");
  const [emergencyContact, setEmergencyContact] = useState<string>("");

  // Substitute fields
  const [substituteId, setSubstituteId] = useState<string>("");
  const [substituteName, setSubstituteName] = useState<string>("");

  const [error, setError] = useState<string>("");
  const [success, setSuccess] = useState<string>("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const payload = {
        applicant_id: "EMP101",
        applicant_name: "Dr. Smith",
        applicant_category: "FACULTY",
        applicant_role: "EMPLOYEE",
        department: "CSE",
        category,
        start_date: startDate,
        end_date: endDate,
        half_day_type: halfDayType,
        purpose,
        is_station_leave: isStationLeave,
        station_address: isStationLeave ? stationAddress : "",
        out_of_station_start: isStationLeave && outStart ? outStart : null,
        out_of_station_end: isStationLeave && outEnd ? outEnd : null,
        emergency_contact: emergencyContact,
        substitute_id: substituteId || null,
        substitute_name: substituteName || null
      };

      const app = await leaveApi.applyForLeave(payload);
      setSuccess(`Leave Application #${app.id} submitted successfully! Status: ${app.status}`);
    } catch (err: any) {
      setError(err.message || "Error submitting application");
    }
  }

  return (
    <div style={{ maxWidth: "700px", margin: "2rem auto", fontFamily: "sans-serif", padding: "1.5rem", border: "1px solid #ccc", borderRadius: "8px" }}>
      <h2>Apply for Leave</h2>

      {error && <div style={{ padding: "0.75rem", backgroundColor: "#f8d7da", color: "#721c24", marginBottom: "1rem", borderRadius: "4px" }}>{error}</div>}
      {success && <div style={{ padding: "0.75rem", backgroundColor: "#d4edda", color: "#155724", marginBottom: "1rem", borderRadius: "4px" }}>{success}</div>}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", fontWeight: "bold" }}>Leave Category:</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)} style={{ width: "100%", padding: "0.5rem" }}>
            <option value="CL">Casual Leave (CL)</option>
            <option value="RH">Restricted Holiday (RH)</option>
            <option value="SCL">Special Casual Leave (SCL)</option>
            <option value="EL">Earned Leave (EL)</option>
            <option value="COL">Commuted Leave (COL)</option>
            <option value="VL">Vacation Leave (VL)</option>
          </select>
        </div>

        <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", fontWeight: "bold" }}>Start Date:</label>
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} required style={{ width: "100%", padding: "0.5rem" }} />
          </div>
          <div style={{ flex: 1 }}>
            <label style={{ display: "block", fontWeight: "bold" }}>End Date:</label>
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} required style={{ width: "100%", padding: "0.5rem" }} />
          </div>
        </div>

        {category === "CL" && (
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontWeight: "bold" }}>Half-Day Option (CL Only):</label>
            <select value={halfDayType} onChange={(e) => setHalfDayType(e.target.value)} style={{ width: "100%", padding: "0.5rem" }}>
              <option value="NONE">Full Day</option>
              <option value="FIRST_HALF">First Half (0.5 Day)</option>
              <option value="SECOND_HALF">Second Half (0.5 Day)</option>
            </select>
          </div>
        )}

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", fontWeight: "bold" }}>Purpose / Reason:</label>
          <textarea value={purpose} onChange={(e) => setPurpose(e.target.value)} required rows={3} style={{ width: "100%", padding: "0.5rem" }} />
        </div>

        {/* Substitute Section */}
        <fieldset style={{ border: "1px solid #ccc", padding: "1rem", borderRadius: "4px", marginBottom: "1rem" }}>
          <legend style={{ fontWeight: "bold" }}>Substitute / Responsibility Holder</legend>
          <div style={{ display: "flex", gap: "1rem" }}>
            <div style={{ flex: 1 }}>
              <label>Substitute ID:</label>
              <input type="text" placeholder="e.g. EMP102" value={substituteId} onChange={(e) => setSubstituteId(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
            </div>
            <div style={{ flex: 1 }}>
              <label>Substitute Name:</label>
              <input type="text" placeholder="e.g. Prof. Jones" value={substituteName} onChange={(e) => setSubstituteName(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
            </div>
          </div>
        </fieldset>

        {/* Station Leave Section */}
        <fieldset style={{ border: "1px solid #ccc", padding: "1rem", borderRadius: "4px", marginBottom: "1rem" }}>
          <legend style={{ fontWeight: "bold" }}>Station Leave Permission (Outside Jabalpur)</legend>
          <label style={{ display: "block", marginBottom: "0.5rem" }}>
            <input type="checkbox" checked={isStationLeave} onChange={(e) => setIsStationLeave(e.target.checked)} />
            Leaving Station / Out of Station
          </label>

          {isStationLeave && (
            <>
              <div style={{ marginBottom: "0.5rem" }}>
                <label>Address during Station Leave:</label>
                <input type="text" value={stationAddress} onChange={(e) => setStationAddress(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
              </div>
              <div style={{ display: "flex", gap: "1rem", marginBottom: "0.5rem" }}>
                <div style={{ flex: 1 }}>
                  <label>Out Date:</label>
                  <input type="date" value={outStart} onChange={(e) => setOutStart(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label>Return Date:</label>
                  <input type="date" value={outEnd} onChange={(e) => setOutEnd(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
                </div>
              </div>
              <div>
                <label>Emergency Contact No:</label>
                <input type="text" value={emergencyContact} onChange={(e) => setEmergencyContact(e.target.value)} style={{ width: "100%", padding: "0.5rem" }} />
              </div>
            </>
          )}
        </fieldset>

        <button type="submit" style={{ width: "100%", padding: "0.75rem", backgroundColor: "#0066cc", color: "#fff", border: "none", borderRadius: "4px", fontSize: "1rem", cursor: "pointer" }}>
          Submit Application
        </button>
      </form>
    </div>
  );
}
