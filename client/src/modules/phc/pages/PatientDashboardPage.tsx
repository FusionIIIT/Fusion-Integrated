import { Link } from "react-router-dom";

import { useAdvisories, useDoctorAvailability, usePatientRecords } from "../api/hooks";

export default function PatientDashboardPage() {
  const records = usePatientRecords();
  const doctors = useDoctorAvailability();
  const advisories = useAdvisories();
  const failed = records.isError || doctors.isError || advisories.isError;
  const loading = records.isPending || doctors.isPending || advisories.isPending;
  return (
    <main>
      <h1>Primary Health Centre</h1>
      {loading && <p role="status">Loading your PHC dashboard…</p>}
      {failed && <p role="alert">The PHC dashboard could not load. Try again shortly.</p>}
      {!loading && !failed && (
        <>
          <section aria-labelledby="dashboard-records">
            <h2 id="dashboard-records">Medical records</h2>
            <p>{records.data?.results.length ?? 0} visits in your record.</p>
            <Link to="/phc/medical-records">View medical records</Link>
          </section>
          <section aria-labelledby="dashboard-doctors">
            <h2 id="dashboard-doctors">Doctor availability</h2>
            {(doctors.data ?? []).length === 0 ? <p>No published schedules are available.</p> :
              <ul>{(doctors.data ?? []).slice(0, 3).map((slot) => (
                <li key={slot.id}>{slot.doctor.display_name}: {slot.starts_at}–{slot.ends_at}</li>
              ))}</ul>}
            <Link to="/phc/doctor-availability">View all availability</Link>
          </section>
          <section aria-labelledby="dashboard-advisories">
            <h2 id="dashboard-advisories">Health advisories</h2>
            {(advisories.data?.results ?? []).length === 0 ? <p>No current advisories.</p> :
              <ul>{(advisories.data?.results ?? []).slice(0, 3).map((item) => (
                <li key={item.id}><strong>{item.title}</strong>: {item.body}</li>
              ))}</ul>}
            <Link to="/phc/advisories">View all advisories</Link>
          </section>
        </>
      )}
    </main>
  );
}
