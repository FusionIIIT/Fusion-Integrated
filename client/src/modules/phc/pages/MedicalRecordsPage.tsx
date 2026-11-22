import { useState } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { useExportMedicalPdf, usePatientRecords } from "../api/hooks";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";
import type { PatientVisit } from "../api/types";

function renderVisit(visit: PatientVisit) {
  return <article>
    <h2>Visit on {visit.visited_on}</h2>
    <p>{visit.notes}</p>
    {visit.prescriptions.length > 0 && <section aria-label="Prescriptions">
      <h3>Prescriptions</h3>
      <ul>{visit.prescriptions.map((prescription) => (
        <li key={prescription.id}>
          <time dateTime={prescription.issued_on}>{prescription.issued_on}</time>: {prescription.details}
        </li>
      ))}</ul>
    </section>}
  </article>;
}

export default function MedicalRecordsPage() {
  const { can } = useAuth();
  const query = usePatientRecords();
  const exportPdf = useExportMedicalPdf();
  const [selected, setSelected] = useState<number[]>([]);
  return <ResourcePanel title="Medical records" data={query.data}
    isPending={query.isPending} isError={query.isError} error={query.error}
    emptyText="No medical visits are recorded yet."
    renderRow={(visit) => <>
      {can("phc.record.export") && <label>
        <input type="checkbox" aria-label={`Include visit from ${visit.visited_on}`}
          checked={selected.includes(visit.id)} onChange={(event) => {
            setSelected((current) => event.target.checked
              ? [...current, visit.id] : current.filter((id) => id !== visit.id));
          }} />
        Include in PDF
      </label>}
      {renderVisit(visit)}
    </>}>
    {can("phc.record.export") && <section aria-label="Medical record PDF export">
      <button type="button" disabled={!selected.length || exportPdf.isPending}
        onClick={() => exportPdf.mutate(selected)}>Download selected records as PDF</button>
      <MutationMessage isPending={exportPdf.isPending} isError={exportPdf.isError}
        error={exportPdf.error} isSuccess={exportPdf.isSuccess} />
    </section>}
  </ResourcePanel>;
}
