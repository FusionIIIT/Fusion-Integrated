import React, { useEffect, useState } from "react";
import { fetchActiveRoles, assignMessRole } from "../api";
import { MessRoleAssignment } from "../types";

export const AdminPage: React.FC = () => {
  const [roles, setRoles] = useState<MessRoleAssignment[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [message, setMessage] = useState<string | null>(null);

  // Form state
  const [employeeId, setEmployeeId] = useState<number>(101);
  const [messId, setMessId] = useState<number>(1);
  const [role, setRole] = useState<string>("CARETAKER");

  const loadRoles = async () => {
    setLoading(true);
    try {
      const data = await fetchActiveRoles();
      setRoles(data);
    } catch (err: unknown) {
      console.error("Failed to load roles", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRoles();
  }, []);

  const handleAssignRole = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await assignMessRole({
        employee_id: employeeId,
        mess_id: messId,
        role,
      });
      setMessage("Role assigned successfully. Prior assignment for this mess/role has been archived.");
      loadRoles();
    } catch (err: unknown) {
      setMessage("Failed to assign role.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-gray-900">MMS Administration & Role Management</h1>
        <p className="text-sm text-gray-500">
          Enforce single active Caretaker / Warden per mess and assign administrative privileges.
        </p>
      </div>

      {message && (
        <div className="rounded-md bg-blue-50 p-4 text-blue-700 text-sm font-medium">
          {message}
        </div>
      )}

      {/* Role Assignment Form */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Assign Mess Role</h2>
        <form onSubmit={handleAssignRole} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label className="block text-xs font-medium text-gray-700">Employee ID</label>
            <input
              type="number"
              value={employeeId}
              onChange={(e) => setEmployeeId(Number(e.target.value))}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
              required
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Mess</label>
            <select
              value={messId}
              onChange={(e) => setMessId(Number(e.target.value))}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            >
              <option value={1}>Mess 1 (Central)</option>
              <option value={2}>Mess 2 (North)</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 p-2 text-sm"
            >
              <option value="CARETAKER">Caretaker</option>
              <option value="WARDEN">Warden</option>
            </select>
          </div>
          <div className="sm:col-span-3">
            <button
              type="submit"
              className="rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              Assign / Reassign Role
            </button>
          </div>
        </form>
      </div>

      {/* Current Active Roles */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Current Active Role Assignments</h2>
        {loading ? (
          <p className="text-sm text-gray-500">Loading roles...</p>
        ) : roles.length === 0 ? (
          <p className="text-sm text-gray-500">No active roles assigned yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">ID</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Employee ID</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Mess</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Role</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Assigned At</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {roles.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2 text-gray-900">#{r.id}</td>
                    <td className="px-4 py-2 text-gray-900">{r.employee_id}</td>
                    <td className="px-4 py-2 text-gray-600">Mess {r.mess_id}</td>
                    <td className="px-4 py-2 font-medium text-gray-800">{r.role}</td>
                    <td className="px-4 py-2 text-gray-600">{new Date(r.assigned_at).toLocaleDateString()}</td>
                    <td className="px-4 py-2">
                      <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-semibold text-green-800">
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
