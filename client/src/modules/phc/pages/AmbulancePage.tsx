import { useState, type FormEvent } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { useAmbulanceUsage, useRecordAmbulanceUsage } from "../api/hooks";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";

export default function AmbulancePage() {
  const { can } = useAuth();
  const logs = useAmbulanceUsage();
  const record = useRecordAmbulanceUsage();
  const [usedAt, setUsedAt] = useState("");
  const [patientName, setPatientName] = useState("");
  const [destination, setDestination] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    record.mutate({ used_at: new Date(usedAt).toISOString(), patient_name: patientName,
      destination });
  }

  return <ResourcePanel title="Ambulance usage" data={logs.data}
    isPending={logs.isPending} isError={logs.isError} error={logs.error}
    emptyText="No ambulance usage has been recorded."
    renderRow={(entry) => <>{new Date(entry.used_at).toLocaleString()}: {entry.patient_name};
      destination {entry.destination}</>}>
    {can("phc.ambulance_usage.create") && <form onSubmit={submit}>
      <h2>Record ambulance usage</h2>
      <label htmlFor="ambulance-time">Time used</label>
      <input id="ambulance-time" type="datetime-local" required value={usedAt}
        onChange={(event) => setUsedAt(event.target.value)} />
      <label htmlFor="ambulance-patient">Patient name</label>
      <input id="ambulance-patient" required value={patientName}
        onChange={(event) => setPatientName(event.target.value)} />
      <label htmlFor="ambulance-destination">Destination</label>
      <input id="ambulance-destination" required value={destination}
        onChange={(event) => setDestination(event.target.value)} />
      <button type="submit" disabled={record.isPending}>Record ambulance use</button>
      <MutationMessage isPending={record.isPending} isError={record.isError}
        error={record.error} isSuccess={record.isSuccess} />
    </form>}
  </ResourcePanel>;
}
