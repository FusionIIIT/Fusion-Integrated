import React, { useEffect, useState } from "react";
import {
  fetchPendingRebates,
  fetchPendingRegistrations,
  openRegistrationWindow,
  reviewRebate,
  reviewRegistration,
  updateMenuItem,
} from "../api";
import { MessRegistration, RebateRequest } from "../types";

export const CaretakerPage: React.FC = () => {
  const [registrations, setRegistrations] = useState<MessRegistration[]>([]);
  const [rebates, setRebates] = useState<RebateRequest[]>([]);
  const [windowName, setWindowName] = useState("Monsoon Term Window");
  const [winStart, setWinStart] = useState("");
  const [winEnd, setWinEnd] = useState("");
  const [menuDay, setMenuDay] = useState("MONDAY");
  const [menuMeal, setMenuMeal] = useState("BREAKFAST");
  const [menuDishes, setMenuDishes] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [regs, rbs] = await Promise.all([
        fetchPendingRegistrations(),
        fetchPendingRebates(),
      ]);
      setRegistrations(regs);
      setRebates(rbs);
    } catch {
      console.error("Failed to load caretaker data");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenWindow = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await openRegistrationWindow({ name: windowName, start_date: winStart, end_date: winEnd });
      setMessage("Registration window opened successfully.");
    } catch {
      setMessage("Failed to open registration window.");
    }
  };

  const handleUpdateMenu = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateMenuItem({ day_of_week: menuDay, meal_time: menuMeal, items: menuDishes });
      setMessage("Daily menu updated successfully.");
      setMenuDishes("");
    } catch {
      setMessage("Failed to update daily menu.");
    }
  };

  const handleReviewRegistration = async (id: number, approve: boolean) => {
    try {
      await reviewRegistration(id, { approve });
      setMessage(`Registration #${id} updated.`);
      loadData();
    } catch {
      setMessage(`Failed to update registration #${id}.`);
    }
  };

  const handleReviewRebate = async (id: number, approve: boolean) => {
    try {
      await reviewRebate(id, { approve });
      setMessage(`Rebate #${id} updated.`);
      loadData();
    } catch {
      setMessage(`Failed to update rebate #${id}.`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Caretaker Operations Panel</h1>
        <p className="text-sm text-gray-500">Manage windows, review applications, and publish menus</p>
      </div>

      {message && (
        <div className="rounded bg-blue-50 p-3 text-sm font-medium text-blue-700">{message}</div>
      )}

      {/* Open Window */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Open Registration Window</h2>
        <form onSubmit={handleOpenWindow} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="block text-xs font-medium text-gray-700">Window Name</label>
            <input
              type="text"
              value={windowName}
              onChange={(e) => setWindowName(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Start Date</label>
            <input
              type="date"
              value={winStart}
              onChange={(e) => setWinStart(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">End Date</label>
            <input
              type="date"
              value={winEnd}
              onChange={(e) => setWinEnd(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div className="sm:col-span-3">
            <button
              type="submit"
              className="rounded bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              Open Window
            </button>
          </div>
        </form>
      </div>

      {/* Update Menu */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Update Daily Menu</h2>
        <form onSubmit={handleUpdateMenu} className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label className="block text-xs font-medium text-gray-700">Day</label>
            <select
              value={menuDay}
              onChange={(e) => setMenuDay(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            >
              {["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"].map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Meal</label>
            <select
              value={menuMeal}
              onChange={(e) => setMenuMeal(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            >
              {["BREAKFAST", "LUNCH", "DINNER"].map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Dishes (comma separated)</label>
            <input
              type="text"
              placeholder="e.g. Rice, Dal, Roti, Salad"
              value={menuDishes}
              onChange={(e) => setMenuDishes(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div className="sm:col-span-3">
            <button
              type="submit"
              className="rounded bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              Save Menu Item
            </button>
          </div>
        </form>
      </div>

      {/* Pending Registrations */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Pending Registrations ({registrations.length})</h2>
        {registrations.length === 0 ? (
          <p className="text-sm text-gray-500">No pending student registrations.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">ID</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Student</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Mess</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Dates</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {registrations.map((r) => (
                  <tr key={r.id}>
                    <td className="px-3 py-2">#{r.id}</td>
                    <td className="px-3 py-2 font-mono">Student #{r.student_id}</td>
                    <td className="px-3 py-2">{r.mess_name}</td>
                    <td className="px-3 py-2">{r.start_date} to {r.end_date || "term"}</td>
                    <td className="px-3 py-2 space-x-2">
                      <button
                        onClick={() => handleReviewRegistration(r.id, true)}
                        className="rounded bg-green-600 px-2 py-1 text-white hover:bg-green-700 font-semibold"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReviewRegistration(r.id, false)}
                        className="rounded bg-red-600 px-2 py-1 text-white hover:bg-red-700 font-semibold"
                      >
                        Reject
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pending Rebates */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Pending Rebates ({rebates.length})</h2>
        {rebates.length === 0 ? (
          <p className="text-sm text-gray-500">No pending rebate requests.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">ID</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Student</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Dates</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Days</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Reason</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {rebates.map((rb) => (
                  <tr key={rb.id}>
                    <td className="px-3 py-2">#{rb.id}</td>
                    <td className="px-3 py-2 font-mono">Student #{rb.student_id}</td>
                    <td className="px-3 py-2">{rb.start_date} to {rb.end_date}</td>
                    <td className="px-3 py-2">{rb.duration_days}</td>
                    <td className="px-3 py-2">{rb.reason}</td>
                    <td className="px-3 py-2 space-x-2">
                      <button
                        onClick={() => handleReviewRebate(rb.id, true)}
                        className="rounded bg-green-600 px-2 py-1 text-white hover:bg-green-700 font-semibold"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReviewRebate(rb.id, false)}
                        className="rounded bg-red-600 px-2 py-1 text-white hover:bg-red-700 font-semibold"
                      >
                        Reject
                      </button>
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
