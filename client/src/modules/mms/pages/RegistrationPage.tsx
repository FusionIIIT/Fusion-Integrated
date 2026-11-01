import React, { useEffect, useState } from "react";
import {
  fetchCurrentWindow,
  fetchMyRegistration,
  submitDeregistration,
  submitRegistration,
} from "../api";
import { MessRegistration, RegistrationWindow } from "../types";

export const RegistrationPage: React.FC = () => {
  const [window, setWindow] = useState<RegistrationWindow | null>(null);
  const [registration, setRegistration] = useState<MessRegistration | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [deregReason, setDeregReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchCurrentWindow().then(setWindow).catch(() => setWindow(null));
    fetchMyRegistration().then(setRegistration).catch(() => setRegistration(null));
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const reg = await submitRegistration({ start_date: startDate, end_date: endDate });
      setRegistration(reg);
      setMessage("Registration submitted successfully.");
    } catch {
      setMessage("Failed to submit registration. Check window dates.");
    }
  };

  const handleDeregister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!registration) return;
    try {
      await submitDeregistration(registration.id, { reason: deregReason });
      setMessage("Deregistration request submitted.");
    } catch {
      setMessage("Failed to submit deregistration request.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Mess Registration</h1>
        <p className="text-sm text-gray-500">Register or deregister for hostel dining services</p>
      </div>

      {message && (
        <div className="rounded bg-blue-50 p-3 text-sm font-medium text-blue-700">{message}</div>
      )}

      {/* Active Window Banner */}
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-800">Current Registration Window</h2>
        {window && window.is_open ? (
          <p className="text-xs text-green-700 mt-1">
            <strong>{window.name}</strong> is OPEN ({window.start_date} to {window.end_date})
          </p>
        ) : (
          <p className="text-xs text-red-600 mt-1">No registration window is currently open.</p>
        )}
      </div>

      {/* Existing Registration Info */}
      {registration ? (
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm space-y-4">
          <h2 className="text-base font-semibold text-gray-800">Your Current Registration</h2>
          <div className="text-sm space-y-1">
            <p><strong>Mess:</strong> {registration.mess_name}</p>
            <p><strong>Status:</strong> {registration.status}</p>
            <p><strong>Duration:</strong> {registration.start_date} to {registration.end_date || "End of Term"}</p>
          </div>

          {registration.status === "REGISTERED" && (
            <form onSubmit={handleDeregister} className="mt-4 space-y-3 border-t pt-4">
              <h3 className="text-sm font-semibold text-gray-700">Request Deregistration</h3>
              <input
                type="text"
                placeholder="Reason for deregistration"
                value={deregReason}
                onChange={(e) => setDeregReason(e.target.value)}
                className="block w-full rounded border border-gray-300 p-2 text-sm"
                required
              />
              <button
                type="submit"
                className="rounded bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700"
              >
                Submit Deregistration
              </button>
            </form>
          )}
        </div>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-gray-800 mb-3">Submit New Registration</h2>
          <form onSubmit={handleRegister} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-gray-700">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              />
            </div>
            <div className="sm:col-span-2">
              <button
                type="submit"
                disabled={!window || !window.is_open}
                className="rounded bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                Apply for Registration
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
