import { useState, type FormEvent } from "react";

import { useCreateVisit, usePatientSearch } from "../api/hooks";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";

export default function VisitsPage() {
  const [search, setSearch] = useState("");
  const [patientId, setPatientId] = useState<number | null>(null);
  const [visitedOn, setVisitedOn] = useState("");
  const [notes, setNotes] = useState("");
  const [details, setDetails] = useState("");
  const [issuedOn, setIssuedOn] = useState("");
  const matches = usePatientSearch(search);
  const create = useCreateVisit();

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (patientId === null) return;
    create.mutate({ patient_user_id: patientId, visited_on: visitedOn, notes,
      prescription_details: details, issued_on: issuedOn });
  }

  return <ResourcePanel title="Patient visits" data={[]} isPending={false} isError={false}
    emptyText="Record a visit for a patient from the institute directory."
    renderRow={() => null}>
    <form onSubmit={submit}>
      <label htmlFor="patient-search">Find patient</label>
      <input id="patient-search" type="search" value={search}
        onChange={(event) => { setSearch(event.target.value); setPatientId(null); }} />
      {search.trim().length < 2 && <p>Enter at least two characters to search the institute directory.</p>}
      {matches.isFetching && <p role="status">Searching the institute directory…</p>}
      {matches.isError && <p role="alert">Patient directory search failed.</p>}
      {matches.data && <fieldset>
        <legend>Select a patient</legend>
        {matches.data.length === 0 ? <p>No directory matches.</p> : matches.data.map((person) => (
          <label key={person.user_id}>
            <input type="radio" name="patient" value={person.user_id}
              checked={patientId === person.user_id}
              onChange={() => setPatientId(person.user_id)} />
            {person.display_name} ({person.kind})
          </label>
        ))}
      </fieldset>}
      <label htmlFor="visit-date">Visit date</label>
      <input id="visit-date" type="date" required value={visitedOn}
        onChange={(event) => setVisitedOn(event.target.value)} />
      <label htmlFor="visit-notes">Symptoms, diagnosis, and clinical remarks</label>
      <textarea id="visit-notes" required value={notes}
        onChange={(event) => setNotes(event.target.value)} />
      <label htmlFor="prescription-details">Medicines, dosage, and instructions</label>
      <textarea id="prescription-details" required value={details}
        onChange={(event) => setDetails(event.target.value)} />
      <label htmlFor="prescription-date">Prescription issue date</label>
      <input id="prescription-date" type="date" required value={issuedOn}
        onChange={(event) => setIssuedOn(event.target.value)} />
      <button type="submit" disabled={create.isPending || patientId === null}>Save visit and prescription</button>
      <MutationMessage isPending={create.isPending} isError={create.isError}
        error={create.error} isSuccess={create.isSuccess} />
    </form>
  </ResourcePanel>;
}
