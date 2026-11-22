import { useDoctorAvailability } from "../api/hooks";
import { ResourcePanel } from "../components/ResourcePanel";

export default function DoctorAvailabilityPage() {
  const query = useDoctorAvailability();
  return <ResourcePanel title="Doctor availability" data={query.data}
    isPending={query.isPending} isError={query.isError} error={query.error}
    emptyText="No published doctor schedules are available."
    renderRow={(slot) => <>
      <strong>{slot.doctor.display_name}</strong> — {slot.doctor.specialization};
      day {slot.day_of_week + 1}, {slot.starts_at} to {slot.ends_at};
      attendance: {slot.attendance_status ?? "not reported"}
    </>} />;
}
