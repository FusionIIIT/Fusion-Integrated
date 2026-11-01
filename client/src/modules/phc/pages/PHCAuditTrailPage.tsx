import { useState } from "react";
import { usePHCAuditTrail } from "../api/hooks";

export default function PHCAuditTrailPage() {
  const [targetType, setTargetType] = useState<string>("");
  const [search, setSearch] = useState("");

  const { data: logs, isLoading, error } = usePHCAuditTrail(targetType || undefined);

  const filteredLogs = (logs || []).filter((l) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      l.target_id.toLowerCase().includes(q) ||
      l.action.toLowerCase().includes(q) ||
      l.details.toLowerCase().includes(q) ||
      (l.actor_username && l.actor_username.toLowerCase().includes(q))
    );
  });

  const getTargetBadge = (type: string) => {
    switch (type) {
      case "PATIENT_RECORD":
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-100 text-blue-800">Clinical Record</span>;
      case "INVENTORY_LEVEL":
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800">Inventory Level</span>;
      case "REIMBURSEMENT_CLAIM":
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-100 text-purple-800">Reimbursement</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-800">{type}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">PHC Audit Trail</h1>
          <p className="text-sm text-slate-500 mt-1">
            Tamper-evident, immutable audit log of clinical record accesses, pharmacy stock adjustments, and financial claims.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            Append-Only Log
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
        <input
          type="text"
          placeholder="Search by action, details, actor, or entity ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full sm:max-w-md border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
        />

        <div className="flex flex-wrap gap-2 w-full sm:w-auto">
          {[
            { label: "All Audit Logs", value: "" },
            { label: "Clinical Records", value: "PATIENT_RECORD" },
            { label: "Inventory Levels", value: "INVENTORY_LEVEL" },
            { label: "Reimbursements", value: "REIMBURSEMENT_CLAIM" },
          ].map((tab) => (
            <button
              key={tab.value}
              onClick={() => setTargetType(tab.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                targetType === tab.value
                  ? "bg-indigo-600 text-white"
                  : "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Loading audit trail records...</div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          Failed to load audit trail logs.
        </div>
      ) : !filteredLogs.length ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-500">
          No audit entries matching filter criteria.
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-700 font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Target Scope</th>
                <th className="px-4 py-3">Entity Ref</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Log Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                    {new Date(log.created_at).toLocaleString(undefined, {
                      dateStyle: "short",
                      timeStyle: "medium",
                    })}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">{getTargetBadge(log.target_type)}</td>
                  <td className="px-4 py-3 font-mono text-slate-900 font-medium">#{log.target_id}</td>
                  <td className="px-4 py-3 font-semibold text-slate-800">{log.action}</td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="font-medium text-slate-900">{log.actor_username || "System"}</span>
                    {log.actor_user_id > 0 && (
                      <span className="text-[10px] text-slate-400 block">UID: {log.actor_user_id}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600 max-w-md truncate" title={log.details}>
                    {log.details}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
