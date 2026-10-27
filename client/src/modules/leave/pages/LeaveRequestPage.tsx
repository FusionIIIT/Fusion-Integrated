import { useState, type FormEvent } from "react";
import {
  useCreateLeaveRequest,
  useLeaveRequests,
  useLeaveTypes,
} from "../api/hooks";

export default function LeaveRequestPage() {
  const types = useLeaveTypes();
  const requests = useLeaveRequests();
  const createRequest = useCreateLeaveRequest();

  const [leaveType, setLeaveType] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [formError, setFormError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError("");

    if (!leaveType || !startDate || !endDate) {
      setFormError("Please complete all fields.");
      return;
    }

    if (endDate < startDate) {
      setFormError("End date cannot be before start date.");
      return;
    }

    try {
      await createRequest.mutateAsync({
        leave_type: Number(leaveType),
        start_date: startDate,
        end_date: endDate,
      });
      setStartDate("");
      setEndDate("");
      setFormError("");
    } catch {
      setFormError("Could not submit the request. Please try again.");
    }
  }

  return (
    <main>
      <h1>Leave Management</h1>
      <h2>Apply for Leave</h2>

      <form onSubmit={submit}>
        <p>
          <label htmlFor="leave-type">Leave category</label>
          <br />
          <select
            id="leave-type"
            value={leaveType}
            onChange={(event) => setLeaveType(event.target.value)}
            required
          >
            <option value="">Select a category</option>
            {(types.data ?? []).map((type) => (
              <option key={type.id} value={type.id}>
                {type.name}
              </option>
            ))}
          </select>
        </p>

        <p>
          <label htmlFor="leave-start">Start date</label>
          <br />
          <input
            id="leave-start"
            type="date"
            value={startDate}
            onChange={(event) => setStartDate(event.target.value)}
            required
          />
        </p>

        <p>
          <label htmlFor="leave-end">End date</label>
          <br />
          <input
            id="leave-end"
            type="date"
            value={endDate}
            onChange={(event) => setEndDate(event.target.value)}
            min={startDate || undefined}
            required
          />
        </p>

        {formError && <p role="alert">{formError}</p>}

        {types.isError && (
          <p role="alert">Could not load leave categories.</p>
        )}

        <button
          type="submit"
          disabled={createRequest.isPending || types.isLoading}
        >
          {createRequest.isPending ? "Submitting..." : "Submit request"}
        </button>
      </form>

      <h2>My Leave Requests</h2>

      {requests.isLoading && <p>Loading requests...</p>}
      {requests.isError && (
        <p role="alert">Could not load your leave requests.</p>
      )}

      {requests.data && requests.data.length === 0 && (
        <p>You have not submitted any leave requests.</p>
      )}

      {requests.data && requests.data.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Category ID</th>
              <th>Start date</th>
              <th>End date</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {requests.data.map((request) => (
              <tr key={request.id}>
                <td>{request.leave_type}</td>
                <td>{request.start_date}</td>
                <td>{request.end_date}</td>
                <td>{request.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
