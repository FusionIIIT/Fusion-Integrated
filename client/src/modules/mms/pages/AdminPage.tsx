import React, { useEffect, useState } from "react";
import { assignMessRole, fetchActiveRoles } from "../api";
import { MessRoleAssignment } from "../types";

export const AdminPage: React.FC = () => {
  const [roles, setRoles] = useState<MessRoleAssignment[]>([]);
  const [empId, setEmpId] = useState(101);
  const [role, setRole] = useState("caretaker");
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [remarks, setRemarks] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const loadRoles = async () => {
    try {
      const data = await fetchActiveRoles();
      setRoles(data);
    } catch {
      console.error("Could not load roles");
    }
  };

  useEffect(() => {
    loadRoles();
  }, []);

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await assignMessRole({
        employee_id: empId,
        role,
        start_date: startDate,
        remarks,
      });
      setMessage("Role assigned successfully. Prior active appointment deactivated.");
      loadRoles();
    } catch {
      setMessage("Failed to assign role.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">Mess Administration</h1>
        <p className="text-sm text-gray-500">Assign operational roles & enforce single active staff invariants</p>
      </div>

      {message && (
        <div className="rounded bg-blue-50 p-3 text-sm font-medium text-blue-700">{message}</div>
      )}

      {/* Role Assignment Form */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Assign Operational Role (BR-MMS-003..004)</h2>
        <form onSubmit={handleAssign} className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <div>
            <label className="block text-xs font-medium text-gray-700">Employee ID</label>
            <input
              type="number"
              value={empId}
              onChange={(e) => setEmpId(Number(e.target.value))}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            >
              <option value="caretaker">Caretaker</option>
              <option value="warden">Warden</option>
            </select>
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
            <label className="block text-xs font-medium text-gray-700">Remarks</label>
            <input
              type="text"
              placeholder="e.g. Term appointment"
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            />
          </div>
          <div className="sm:col-span-4">
            <button
              type="submit"
              className="rounded bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700"
            >
              Assign / Reassign Role
            </button>
          </div>
        </form>
      </div>

      {/* Active Roles */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Active Operational Staff</h2>
        {roles.length === 0 ? (
          <p className="text-sm text-gray-500">No active staff assignments found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-xs">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">ID</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Employee</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Role</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Appointed On</th>
                  <th className="px-3 py-2 text-left font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {roles.map((r) => (
                  <tr key={r.id}>
                    <td className="px-3 py-2">#{r.id}</td>
                    <td className="px-3 py-2 font-mono">Employee #{r.employee_id}</td>
                    <td className="px-3 py-2 font-semibold capitalize">{r.role}</td>
                    <td className="px-3 py-2">{r.start_date}</td>
                    <td className="px-3 py-2">
                      <span className="rounded bg-green-100 px-2 py-0.5 text-green-800 font-semibold">
                        Active
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
