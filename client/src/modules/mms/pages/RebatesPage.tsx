import React, { useEffect, useState } from "react";
import { fetchMyRebates, submitRebate } from "../api";
import { RebateRequest } from "../types";

export const RebatesPage: React.FC = () => {
  const [rebates, setRebates] = useState<RebateRequest[]>([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const loadRebates = async () => {
    try {
      const data = await fetchMyRebates();
      setRebates(data);
    } catch {
      console.error("Could not load rebates");
    }
  };

  useEffect(() => {
    loadRebates();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await submitRebate({ start_date: startDate, end_date: endDate, reason });
      setMessage("Rebate application submitted successfully.");
      setStartDate("");
      setEndDate("");
      setReason("");
      loadRebates();
    } catch {
      setMessage("Failed to apply. Must be >= 3 days, 1-day advance notice, and non-overlapping.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Student Meal Rebates</h1>
        <p className="text-sm text-gray-500">Apply for meal rebate credits during official leave</p>
      </div>

      {message && (
        <div className="rounded bg-blue-50 p-3 text-sm font-medium text-blue-700">{message}</div>
      )}

      {/* Rebate Rules Notice */}
      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4 text-xs text-yellow-800 space-y-1">
        <p className="font-semibold">Rebate Business Rules (BR-MMS-021..023):</p>
        <p>• Minimum duration: 3 consecutive days.</p>
        <p>• Advance notice: Must apply at least 1 calendar day before start date.</p>
        <p>• Non-overlapping: Cannot overlap with existing pending or approved rebates.</p>
      </div>

      {/* Application Form */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Apply for Rebate</h2>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
              required
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-700">Reason</label>
            <input
              type="text"
              placeholder="e.g. Conference, Family Event"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div className="sm:col-span-2">
            <button
              type="submit"
              className="rounded bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              Submit Rebate Application
            </button>
          </div>
        </form>
      </div>

      {/* Rebates History */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Rebates History</h2>
        {rebates.length === 0 ? (
          <p className="text-sm text-gray-500">No rebate requests found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">ID</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Period</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Days</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Reason</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {rebates.map((rb) => (
                  <tr key={rb.id}>
                    <td className="px-3 py-2 font-mono">#{rb.id}</td>
                    <td className="px-3 py-2">{rb.start_date} to {rb.end_date}</td>
                    <td className="px-3 py-2">{rb.duration_days}</td>
                    <td className="px-3 py-2">{rb.reason}</td>
                    <td className="px-3 py-2 font-semibold">
                      <span className={rb.status === "APPROVED" ? "text-green-600" : rb.status === "PENDING" ? "text-yellow-600" : "text-red-600"}>
                        {rb.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
