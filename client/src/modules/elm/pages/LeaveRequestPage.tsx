import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { errorMessage } from "../../../lib/http";
import { getLeaveCategories, submitLeaveApplication } from "../api/api";
import type { LeaveCategory } from "../api/types";

type FormState = {
  leave_category_code: string;
  requested_start: string;
  requested_end: string;
  purpose: string;
  halftype: string;
  station_leave: boolean;
  station_leave_details: string;
};

const EMPTY_FORM: FormState = {
  leave_category_code: "",
  requested_start: "",
  requested_end: "",
  purpose: "",
  halftype: "",
  station_leave: false,
  station_leave_details: "",
};

export const LeaveRequestPage = () => {
  const navigate = useNavigate();
  const [categories, setCategories] = useState<LeaveCategory[]>([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getLeaveCategories()
      .then(setCategories)
      .catch((cause: unknown) => setError(errorMessage(cause)))
      .finally(() => setLoading(false));
  }, []);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      await submitLeaveApplication(form);
      navigate("/elm/my-applications");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  }

  const halfDayEnabled = form.leave_category_code === "CL"
    && form.requested_start === form.requested_end;

  return (
    <main className="leave-request-page">
      <h2>Request Leave</h2>
      {error && <p role="alert">{error}</p>}
      {loading ? <p>Loading leave categories…</p> : (
        <form onSubmit={submit}>
          <label>
            Leave category
            <select required value={form.leave_category_code}
              onChange={(event) => update("leave_category_code", event.target.value)}>
              <option value="">Choose a category</option>
              {categories.map((category) => (
                <option key={category.code} value={category.code}>
                  {category.code} — {category.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Start date
            <input required type="date" value={form.requested_start}
              onChange={(event) => update("requested_start", event.target.value)} />
          </label>
          <label>
            End date
            <input required type="date" min={form.requested_start || undefined}
              value={form.requested_end}
              onChange={(event) => update("requested_end", event.target.value)} />
          </label>
          {halfDayEnabled && (
            <label>
              CL duration
              <select value={form.halftype}
                onChange={(event) => update("halftype", event.target.value)}>
                <option value="">Full day</option>
                <option value="FIRST_HALF">First half</option>
                <option value="SECOND_HALF">Second half</option>
              </select>
            </label>
          )}
          <label>
            Purpose / reason
            <textarea required maxLength={4000} value={form.purpose}
              onChange={(event) => update("purpose", event.target.value)} />
          </label>
          <label>
            <input type="checkbox" checked={form.station_leave}
              onChange={(event) => update("station_leave", event.target.checked)} />
            I will be outside Jabalpur during this leave
          </label>
          {form.station_leave && (
            <label>
              Station Leave destination and details
              <textarea required maxLength={2000} value={form.station_leave_details}
                onChange={(event) => update("station_leave_details", event.target.value)} />
            </label>
          )}
          <button type="submit" disabled={saving || !form.leave_category_code}>
            {saving ? "Submitting…" : "Submit request"}
          </button>
        </form>
      )}
    </main>
  );
};
