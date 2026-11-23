import { useState, type FormEvent } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { useCreateSchedule, useDoctorSchedules, usePublishSchedule } from "../api/hooks";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function SchedulesPage() {
  const { can } = useAuth();
  const slots = useDoctorSchedules();
  const create = useCreateSchedule();
  const publish = usePublishSchedule();
  const [name, setName] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [day, setDay] = useState("0");
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate({ display_name: name, specialization, day_of_week: Number(day),
      starts_at: startsAt, ends_at: endsAt });
  }

  return <ResourcePanel title="Doctor schedules" data={slots.data}
    isPending={slots.isPending} isError={slots.isError} error={slots.error}
    emptyText="No doctor schedule slots have been created."
    renderRow={(slot) => <article>
      <strong>{slot.doctor.display_name}</strong>, {slot.doctor.specialization};
      {weekdays[slot.day_of_week]}, {slot.starts_at}–{slot.ends_at}; {slot.publication}
      {slot.publication === "draft" && can("phc.doctor_schedule.publish") &&
        <button type="button" onClick={() => publish.mutate(slot.id)}>Publish schedule</button>}
    </article>}>
    {can("phc.doctor_schedule.create") && <form onSubmit={submit}>
      <h2>Create a doctor schedule</h2>
      <label htmlFor="doctor-name">Doctor display name</label>
      <input id="doctor-name" required value={name}
        onChange={(event) => setName(event.target.value)} />
      <label htmlFor="doctor-specialization">Specialization</label>
      <input id="doctor-specialization" required value={specialization}
        onChange={(event) => setSpecialization(event.target.value)} />
      <label htmlFor="schedule-day">Day of week</label>
      <select id="schedule-day" value={day} onChange={(event) => setDay(event.target.value)}>
        {weekdays.map((weekday, index) => <option key={weekday} value={index}>{weekday}</option>)}
      </select>
      <label htmlFor="schedule-start">Starts at</label>
      <input id="schedule-start" type="time" required value={startsAt}
        onChange={(event) => setStartsAt(event.target.value)} />
      <label htmlFor="schedule-end">Ends at</label>
      <input id="schedule-end" type="time" required value={endsAt}
        onChange={(event) => setEndsAt(event.target.value)} />
      <button type="submit" disabled={create.isPending}>Create schedule</button>
      <MutationMessage isPending={create.isPending} isError={create.isError}
        error={create.error} isSuccess={create.isSuccess} />
    </form>}
    {publish.isError && <p role="alert">{publish.error instanceof Error
      ? publish.error.message : "The schedule could not be published."}</p>}
  </ResourcePanel>;
}
