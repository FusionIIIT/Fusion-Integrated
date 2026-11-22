import { useState, type FormEvent } from "react";

import { useDoctorAttendance, useDoctorSchedules, useSetAttendance } from "../api/hooks";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";

export default function AttendancePage() {
  const attendance = useDoctorAttendance();
  const schedules = useDoctorSchedules();
  const update = useSetAttendance();
  const [doctorId, setDoctorId] = useState("");
  const [status, setStatus] = useState<"available" | "departed">("available");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    update.mutate({ doctor_id: Number(doctorId), status });
  }

  return <ResourcePanel title="Doctor attendance" data={attendance.data}
    isPending={attendance.isPending || schedules.isPending}
    isError={attendance.isError || schedules.isError} error={attendance.error ?? schedules.error}
    emptyText="No doctor attendance has been recorded today."
    renderRow={(entry) => <>{entry.doctor.display_name}: {entry.status} on {entry.attendance_date}</>}>
    <form onSubmit={submit}>
      <label htmlFor="attendance-doctor">Doctor</label>
      <select id="attendance-doctor" required value={doctorId}
        onChange={(event) => setDoctorId(event.target.value)}>
        <option value="">Choose a doctor</option>
        {[...new Map((schedules.data?.results ?? []).map((slot) =>
          [slot.doctor.id, slot.doctor])).values()].map((doctor) => (
            <option key={doctor.id} value={doctor.id}>{doctor.display_name}</option>
          ))}
      </select>
      <label htmlFor="attendance-status">Attendance status</label>
      <select id="attendance-status" value={status}
        onChange={(event) => setStatus(event.target.value as "available" | "departed")}>
        <option value="available">Available</option>
        <option value="departed">Departed</option>
      </select>
      <button type="submit" disabled={!doctorId || update.isPending}>Save attendance</button>
      <MutationMessage isPending={update.isPending} isError={update.isError}
        error={update.error} isSuccess={update.isSuccess} />
    </form>
  </ResourcePanel>;
}
