/** Apply for Leave form.
 *
 *  Fix history:
 *  - C1.1: replaced fetch()+localStorage with shared axios http instance.
 *  - C1.2: URL corrected to /elm/leave-types/ and /elm/requests/ (/api/v1 is
 *           the base URL in http.ts, so the prefix must NOT be repeated here).
 *  - C1.3: payload field name corrected from leaveType to leave_type.
 *  - C1.4: leave type list is now fetched from the backend, not hardcoded.
 *  - C1.5: real loading, empty and error states — no SAMPLE_DATA, no silent catch.
 *  - C1.6: form is only rendered when the caller has elm.leave_request.create.
 */
import React, { useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthProvider";
import { http, errorMessage } from "../../lib/http";
import type { LeaveType, ApplyLeavePayload } from "./api/types";

const ApplyLeave: React.FC = () => {
  const { can } = useAuth();
  const canApply = can("elm.leave_request.create");

  // ── Leave type list ────────────────────────────────────────────────────────
  const [leaveTypes, setLeaveTypes]   = useState<LeaveType[]>([]);
  const [typesLoading, setTypesLoading] = useState(false);
  const [typesError, setTypesError]   = useState<string | null>(null);

  useEffect(() => {
    if (!canApply) return;
    setTypesLoading(true);
    setTypesError(null);
    http
      .get<{ results: LeaveType[] }>("/elm/leave-types/")
      .then((r) => setLeaveTypes(r.data.results ?? []))
      .catch((e) => setTypesError(errorMessage(e)))
      .finally(() => setTypesLoading(false));
  }, [canApply]);

  // ── Form state ─────────────────────────────────────────────────────────────
  const [form, setForm] = useState<ApplyLeavePayload>({
    leave_type: 0,
    start_date: "",
    end_date: "",
    reason: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted]   = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>,
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: name === "leave_type" ? Number(value) : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      await http.post("/elm/requests/", form);
      setSubmitted(true);
    } catch (err) {
      setSubmitError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  // ── Guard ──────────────────────────────────────────────────────────────────
  if (!canApply) {
    return (
      <div style={{ padding: "2rem" }}>
        <p>You do not have permission to apply for leave.</p>
      </div>
    );
  }

  if (submitted) {
    return (
      <div style={{ padding: "2rem" }}>
        <h2>Leave application submitted successfully!</h2>
        <button onClick={() => { setSubmitted(false); setForm({ leave_type: 0, start_date: "", end_date: "", reason: "" }); }}>
          Submit another
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 480, margin: "2rem auto", padding: "1.5rem", border: "1px solid #ddd", borderRadius: 8 }}>
      <h2>Apply for Leave</h2>

      {typesError && <p style={{ color: "red" }}>Could not load leave types: {typesError}</p>}
      {submitError && <p style={{ color: "red" }}>{submitError}</p>}

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="elm-leave-type">Leave Type</label>
          {typesLoading ? (
            <p>Loading leave types…</p>
          ) : leaveTypes.length === 0 && !typesError ? (
            <p>No leave types configured.</p>
          ) : (
            <select
              id="elm-leave-type"
              name="leave_type"
              value={form.leave_type || ""}
              onChange={handleChange}
              required
              style={{ display: "block", width: "100%" }}
            >
              <option value="">-- Select --</option>
              {leaveTypes.map((lt) => (
                <option key={lt.id} value={lt.id}>
                  {lt.name}
                </option>
              ))}
            </select>
          )}
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="elm-start-date">Start Date</label>
          <input
            id="elm-start-date"
            type="date"
            name="start_date"
            value={form.start_date}
            onChange={handleChange}
            required
            style={{ display: "block", width: "100%" }}
          />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="elm-end-date">End Date</label>
          <input
            id="elm-end-date"
            type="date"
            name="end_date"
            value={form.end_date}
            onChange={handleChange}
            required
            style={{ display: "block", width: "100%" }}
          />
        </div>
        <div style={{ marginBottom: "1rem" }}>
          <label htmlFor="elm-reason">Reason</label>
          <textarea
            id="elm-reason"
            name="reason"
            value={form.reason}
            onChange={handleChange}
            rows={3}
            style={{ display: "block", width: "100%" }}
          />
        </div>
        <button type="submit" disabled={submitting || typesLoading}>
          {submitting ? "Submitting…" : "Submit Application"}
        </button>
      </form>
    </div>
  );
};

export default ApplyLeave;
