import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { errorMessage, http } from "../../../lib/http";

type LeaveRequest = {
  id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
};
type Page<T> = { results: T[] };

export default function RequestsPage() {
  const client = useQueryClient();
  const [leaveType, setLeaveType] = useState("CL");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const requests = useQuery({
    queryKey: ["leave-cell", "requests"],
    queryFn: async () => (await http.get<Page<LeaveRequest>>("/leave/requests/")).data.results,
  });
  const create = useMutation({
    mutationFn: async (data: Omit<LeaveRequest, "id" | "status">) =>
      (await http.post<LeaveRequest>("/leave/requests/", data)).data,
    onSuccess: () => {
      setReason("");
      client.invalidateQueries({ queryKey: ["leave-cell", "requests"] });
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate({ leave_type: leaveType, start_date: startDate, end_date: endDate, reason });
  }

  return <main>
    <h1>Leave Requests</h1>
    <form onSubmit={submit}>
      <label>Leave type <select value={leaveType} onChange={(e) => setLeaveType(e.target.value)}>
        <option value="CL">Casual Leave</option><option value="RH">Restricted Holiday</option>
        <option value="SCL">Special Casual Leave</option><option value="EL">Earned Leave</option>
        <option value="COL">Compensatory Off</option><option value="VL">Vacation Leave</option>
      </select></label>{" "}
      <label>From <input required type="date" value={startDate}
        onChange={(e) => setStartDate(e.target.value)} /></label>{" "}
      <label>To <input required type="date" value={endDate}
        onChange={(e) => setEndDate(e.target.value)} /></label>{" "}
      <label>Reason <input value={reason} onChange={(e) => setReason(e.target.value)} /></label>{" "}
      <button type="submit" disabled={create.isPending}>Submit request</button>
    </form>
    {create.isError && <p role="alert">{errorMessage(create.error)}</p>}
    {requests.isPending && <p>Loading requests…</p>}
    {requests.isError && <p role="alert">{errorMessage(requests.error)}</p>}
    {requests.data && <table>
      <thead><tr><th>Type</th><th>From</th><th>To</th><th>Reason</th><th>Status</th></tr></thead>
      <tbody>{requests.data.map((row) => <tr key={row.id}>
        <td>{row.leave_type}</td><td>{row.start_date}</td><td>{row.end_date}</td>
        <td>{row.reason}</td><td>{row.status}</td>
      </tr>)}</tbody>
    </table>}
  </main>;
}
