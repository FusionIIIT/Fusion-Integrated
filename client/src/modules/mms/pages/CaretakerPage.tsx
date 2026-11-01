import React, { useEffect, useState } from "react";
import {
  fetchPendingRegistrations,
  reviewRegistration,
  fetchPendingRebates,
  reviewRebate,
  openRegistrationWindow,
  updateMenuItem,
} from "../api";
import { RegistrationWindow, MessRegistration, RebateRequest } from "../types";

export const CaretakerPage: React.FC = () => {
  const [registrations, setRegistrations] = useState<MessRegistration[]>([]);
  const [rebates, setRebates] = useState<RebateRequest[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [message, setMessage] = useState<string | null>(null);

  // Registration window form state
  const [academicYear, setAcademicYear] = useState<string>("2024-2025");
  const [semester, setSemester] = useState<string>("Monsoon");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");

  // Menu update form state
  const [menuMessId, setMenuMessId] = useState<number>(1);
  const [dayOfWeek, setDayOfWeek] = useState<string>("MONDAY");
  const [mealTime, setMealTime] = useState<string>("BREAKFAST");
  const [dishNames, setDishNames] = useState<string>("");

  const loadData = async () => {
    setLoading(true);
    try {
      const [regsData, rebatesData] = await Promise.all([
        fetchPendingRegistrations(),
        fetchPendingRebates(),
      ]);
      setRegistrations(regsData);
      setRebates(rebatesData);
    } catch (err: unknown) {
      console.error("Failed to load caretaker data", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenWindow = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await openRegistrationWindow({
        academic_year: academicYear,
        semester,
        start_date: startDate,
        end_date: endDate,
      });
      setMessage("Registration window opened successfully.");
    } catch (err: unknown) {
      setMessage("Failed to open registration window.");
    }
  };

  const handleReviewRegistration = async (id: number, status: "APPROVED" | "REJECTED") => {
    try {
      await reviewRegistration(id, { status });
      setMessage(`Registration #${id} marked as ${status}.`);
      loadData();
    } catch (err: unknown) {
      setMessage(`Failed to update registration #${id}.`);
    }
  };

  const handleReviewRebate = async (id: number, status: "APPROVED" | "REJECTED") => {
    try {
      await reviewRebate(id, { status });
      setMessage(`Rebate #${id} marked as ${status}.`);
      loadData();
    } catch (err: unknown) {
      setMessage(`Failed to update rebate #${id}.`);
    }
  };

  const handleUpdateMenu = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateMenuItem({
        mess_id: menuMessId,
        day_of_week: dayOfWeek,
        meal_time: mealTime,
        dish_names: dishNames,
      });
      setMessage("Menu item updated successfully.");
      setDishNames("");
    } catch (err: unknown) {
      setMessage("Failed to update menu item.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Caretaker Operations</h1>
        <p className="text-sm text-gray-500">
          Manage registration windows, review registrations & rebates, and update daily mess menus.
        </p>
      </div>

      {message && (
        <div className="rounded-md bg-blue-50 p-4 text-blue-700 text-sm font-medium">
          {message}
        </div>
      )}

      {/* Open Registration Window */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Open Registration Window</h2>
        <form onSubmit={handleOpenWindow} className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Academic Year</label>
            <input
              type="text"
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Semester</label>
            <input
              type="text"
              value={semester}
              onChange={(e) => setSemester(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
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
          <div className="sm:col-span-4">
            <button
              type="submit"
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              Open Window
            </button>
          </div>
        </form>
      </div>

      {/* Menu Item Update */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Update Daily Menu</h2>
        <form onSubmit={handleUpdateMenu} className="grid grid-cols-1 gap-4 sm:grid-cols-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Mess</label>
            <select
              value={menuMessId}
              onChange={(e) => setMenuMessId(Number(e.target.value))}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            >
              <option value={1}>Mess 1 (Central)</option>
              <option value={2}>Mess 2 (North)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Day of Week</label>
            <select
              value={dayOfWeek}
              onChange={(e) => setDayOfWeek(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            >
              <option value="MONDAY">Monday</option>
              <option value="TUESDAY">Tuesday</option>
              <option value="WEDNESDAY">Wednesday</option>
              <option value="THURSDAY">Thursday</option>
              <option value="FRIDAY">Friday</option>
              <option value="SATURDAY">Saturday</option>
              <option value="SUNDAY">Sunday</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Meal Time</label>
            <select
              value={mealTime}
              onChange={(e) => setMealTime(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            >
              <option value="BREAKFAST">Breakfast</option>
              <option value="LUNCH">Lunch</option>
              <option value="SNACKS">Snacks</option>
              <option value="DINNER">Dinner</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Dishes (Comma-separated)</label>
            <input
              type="text"
              placeholder="e.g. Masala Dosa, Sambhar, Chutney, Tea"
              value={dishNames}
              onChange={(e) => setDishNames(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div className="sm:col-span-4">
            <button
              type="submit"
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              Save Menu Item
            </button>
          </div>
        </form>
      </div>

      {/* Pending Registrations */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pending Student Registrations</h2>
        {registrations.length === 0 ? (
          <p className="text-sm text-gray-500">No pending registrations to review.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">ID</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Student ID</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Mess</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Period</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {registrations.map((reg) => (
                  <tr key={reg.id}>
                    <td className="px-4 py-2 text-gray-900">#{reg.id}</td>
                    <td className="px-4 py-2 text-gray-900">{reg.student_id}</td>
                    <td className="px-4 py-2 text-gray-600">Mess {reg.mess_id}</td>
                    <td className="px-4 py-2 text-gray-600">
                      {reg.academic_year} ({reg.semester})
                    </td>
                    <td className="px-4 py-2 space-x-2">
                      <button
                        onClick={() => handleReviewRegistration(reg.id, "APPROVED")}
                        className="rounded bg-green-600 px-2 py-1 text-xs font-semibold text-white hover:bg-green-700"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReviewRegistration(reg.id, "REJECTED")}
                        className="rounded bg-red-600 px-2 py-1 text-xs font-semibold text-white hover:bg-red-700"
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
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Pending Rebate Requests</h2>
        {rebates.length === 0 ? (
          <p className="text-sm text-gray-500">No pending rebates to review.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">ID</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Student ID</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Dates</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Days</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Reason</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {rebates.map((rebate) => (
                  <tr key={rebate.id}>
                    <td className="px-4 py-2 text-gray-900">#{rebate.id}</td>
                    <td className="px-4 py-2 text-gray-900">{rebate.student_id}</td>
                    <td className="px-4 py-2 text-gray-600">
                      {rebate.start_date} to {rebate.end_date}
                    </td>
                    <td className="px-4 py-2 text-gray-600">{rebate.days_count}</td>
                    <td className="px-4 py-2 text-gray-600">{rebate.reason}</td>
                    <td className="px-4 py-2 space-x-2">
                      <button
                        onClick={() => handleReviewRebate(rebate.id, "APPROVED")}
                        className="rounded bg-green-600 px-2 py-1 text-xs font-semibold text-white hover:bg-green-700"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReviewRebate(rebate.id, "REJECTED")}
                        className="rounded bg-red-600 px-2 py-1 text-xs font-semibold text-white hover:bg-red-700"
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

