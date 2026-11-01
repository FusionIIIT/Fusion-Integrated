import { useState } from "react";
import { useAmbulanceLogs, useLogAmbulance } from "../api/hooks";
import type { AmbulanceLog } from "../api/types";

export default function AmbulanceLogsPage() {
  const [showLogModal, setShowLogModal] = useState(false);
  const [editingTrip, setEditingTrip] = useState<AmbulanceLog | null>(null);
  const [search, setSearch] = useState("");

  const { data: logs, isLoading, error } = useAmbulanceLogs();
  const logAmbulance = useLogAmbulance();

  // Form State
  const [patientName, setPatientName] = useState("");
  const [patientUserId, setPatientUserId] = useState<string>("");
  const [destination, setDestination] = useState("");
  const [departureTime, setDepartureTime] = useState("");
  const [returnTime, setReturnTime] = useState("");
  const [driverName, setDriverName] = useState("");
  const [reason, setReason] = useState("");
  const [formError, setFormError] = useState("");

  const openNewTripModal = () => {
    setEditingTrip(null);
    setPatientName("");
    setPatientUserId("");
    setDestination("");
    setDepartureTime(new Date().toISOString().slice(0, 16));
    setReturnTime("");
    setDriverName("");
    setReason("");
    setFormError("");
    setShowLogModal(true);
  };

  const openUpdateReturnModal = (trip: AmbulanceLog) => {
    setEditingTrip(trip);
    setPatientName(trip.patient_name);
    setPatientUserId(trip.patient_user_id ? String(trip.patient_user_id) : "");
    setDestination(trip.destination);
    setDepartureTime(trip.departure_time ? new Date(trip.departure_time).toISOString().slice(0, 16) : "");
    setReturnTime(trip.return_time ? new Date(trip.return_time).toISOString().slice(0, 16) : new Date().toISOString().slice(0, 16));
    setDriverName(trip.driver_name);
    setReason(trip.reason);
    setFormError("");
    setShowLogModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    if (!patientName.trim()) {
      setFormError("Patient name is required.");
      return;
    }
    if (!destination.trim()) {
      setFormError("Hospital destination is required.");
      return;
    }
    if (!driverName.trim()) {
      setFormError("Driver name is required.");
      return;
    }
    if (!departureTime) {
      setFormError("Departure timestamp is required.");
      return;
    }

    try {
      const payload: Partial<AmbulanceLog> & { id?: number } = {
        patient_name: patientName.trim(),
        patient_user_id: patientUserId.trim() ? Number(patientUserId) : null,
        destination: destination.trim(),
        departure_time: departureTime,
        return_time: returnTime || null,
        driver_name: driverName.trim(),
        reason: reason.trim(),
      };
      if (editingTrip) {
        payload.id = editingTrip.id;
      }
      await logAmbulance.mutateAsync(payload);
      setShowLogModal(false);
    } catch (err: any) {
      setFormError(err.response?.data?.error || err.message || "Failed to save ambulance log entry.");
    }
  };

  const filteredLogs = (logs || []).filter((l) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      l.patient_name.toLowerCase().includes(q) ||
      l.destination.toLowerCase().includes(q) ||
      l.driver_name.toLowerCase().includes(q) ||
      l.reason.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Ambulance Dispatch Log</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track emergency campus patient dispatches, destination hospitals, transit times, and drivers.
          </p>
        </div>
        <button
          onClick={openNewTripModal}
          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
        >
          Record Emergency Dispatch
        </button>
      </div>

      {/* Filter / Search Bar */}
      <div className="flex items-center gap-4">
        <input
          type="text"
          placeholder="Search by patient, destination, driver, or reason..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      {/* Ambulance Logs Table */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Loading ambulance transit logs...</div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          Failed to load ambulance records.
        </div>
      ) : !filteredLogs.length ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-500">
          No ambulance dispatch logs recorded.
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-700 font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Patient</th>
                <th className="px-4 py-3">Destination</th>
                <th className="px-4 py-3">Departure</th>
                <th className="px-4 py-3">Return</th>
                <th className="px-4 py-3">Driver</th>
                <th className="px-4 py-3">Emergency Reason</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredLogs.map((log) => {
                const isOngoing = !log.return_time;
                return (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">{log.patient_name}</div>
                      {log.patient_user_id && (
                        <div className="text-[11px] text-slate-400">UID: {log.patient_user_id}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-800">{log.destination}</td>
                    <td className="px-4 py-3">
                      {new Date(log.departure_time).toLocaleString(undefined, {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </td>
                    <td className="px-4 py-3">
                      {log.return_time ? (
                        new Date(log.return_time).toLocaleString(undefined, {
                          dateStyle: "short",
                          timeStyle: "short",
                        })
                      ) : (
                        <span className="text-amber-600 italic">In Transit</span>
                      )}
                    </td>
                    <td className="px-4 py-3">{log.driver_name}</td>
                    <td className="px-4 py-3 max-w-xs truncate" title={log.reason}>
                      {log.reason}
                    </td>
                    <td className="px-4 py-3">
                      {isOngoing ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 animate-pulse">
                          Active Dispatch
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800">
                          Completed
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {isOngoing ? (
                        <button
                          onClick={() => openUpdateReturnModal(log)}
                          className="text-xs font-semibold text-indigo-600 hover:text-indigo-900 bg-indigo-50 hover:bg-indigo-100 px-2.5 py-1 rounded border border-indigo-200"
                        >
                          Mark Returned
                        </button>
                      ) : (
                        <button
                          onClick={() => openUpdateReturnModal(log)}
                          className="text-xs text-slate-500 hover:text-slate-800"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Log Trip Modal */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 border-b pb-2">
              {editingTrip ? "Update Ambulance Trip" : "Record Emergency Ambulance Dispatch"}
            </h2>
            {formError && (
              <div className="p-3 bg-red-50 text-red-700 rounded text-xs border border-red-200">
                {formError}
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Patient Full Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={patientName}
                  onChange={(e) => setPatientName(e.target.value)}
                  placeholder="Patient Name..."
                  className="w-full border border-slate-300 rounded p-2"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Patient User ID (Optional)
                </label>
                <input
                  type="number"
                  value={patientUserId}
                  onChange={(e) => setPatientUserId(e.target.value)}
                  placeholder="Campus User ID if registered student/staff..."
                  className="w-full border border-slate-300 rounded p-2"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Destination Hospital / Facility <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  placeholder="e.g. City Civil Hospital, Jabalpur..."
                  className="w-full border border-slate-300 rounded p-2"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Departure Time <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="datetime-local"
                    required
                    value={departureTime}
                    onChange={(e) => setDepartureTime(e.target.value)}
                    className="w-full border border-slate-300 rounded p-2"
                  />
                </div>
                <div>
                  <label className="block font-medium text-slate-700 mb-1">
                    Return Time (if returned)
                  </label>
                  <input
                    type="datetime-local"
                    value={returnTime}
                    onChange={(e) => setReturnTime(e.target.value)}
                    className="w-full border border-slate-300 rounded p-2"
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Driver Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={driverName}
                  onChange={(e) => setDriverName(e.target.value)}
                  placeholder="Driver's Full Name..."
                  className="w-full border border-slate-300 rounded p-2"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700 mb-1">
                  Emergency Reason / Chief Medical Incident <span className="text-red-500">*</span>
                </label>
                <textarea
                  required
                  rows={2}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Specify trauma, cardiac, sudden acute illness details..."
                  className="w-full border border-slate-300 rounded p-2"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={logAmbulance.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded font-medium disabled:opacity-50"
                >
                  {logAmbulance.isPending ? "Saving..." : "Save Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
