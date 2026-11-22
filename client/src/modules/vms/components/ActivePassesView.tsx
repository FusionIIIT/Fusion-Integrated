import React, { useEffect, useState } from "react";
import { fetchActivePasses, fetchActiveVisits } from "../api/client";
import { VisitorPass, VisitLog } from "../api/types";

export const ActivePassesView: React.FC = () => {
  const [passes, setPasses] = useState<VisitorPass[]>([]);
  const [visits, setVisits] = useState<VisitLog[]>([]);

  useEffect(() => {
    fetchActivePasses().then(setPasses).catch(console.error);
    fetchActiveVisits().then(setVisits).catch(console.error);
  }, []);

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-bold mb-3 text-gray-800">Currently On-Campus Visitors ({visits.length})</h3>
        {visits.length === 0 ? (
          <p className="text-sm text-gray-500">No visitors currently on-site.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead>
                <tr className="bg-gray-50">
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Visitor</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Entry Gate</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Check-in Time</th>
                  <th className="px-4 py-2 text-left font-medium text-gray-500">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {visits.map((v) => (
                  <tr key={v.log_id}>
                    <td className="px-4 py-2 font-medium">{v.visitor_name}</td>
                    <td className="px-4 py-2">{v.entry_gate_name}</td>
                    <td className="px-4 py-2">{new Date(v.check_in_time).toLocaleTimeString()}</td>
                    <td className="px-4 py-2"><span className="bg-green-100 text-green-800 px-2 py-0.5 rounded text-xs">ON-SITE</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-bold mb-3 text-gray-800">Active Issued Passes ({passes.length})</h3>
        {passes.length === 0 ? (
          <p className="text-sm text-gray-500">No active passes.</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {passes.map((p) => (
              <div key={p.pass_id} className="border border-gray-200 rounded p-4 bg-gray-50">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-bold text-gray-800">{p.visitor_name}</h4>
                    <p className="text-xs text-gray-500">Host: {p.host_name}</p>
                    <p className="text-xs text-gray-500">Type: {p.pass_type}</p>
                  </div>
                  <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded">{p.status}</span>
                </div>
                <div className="mt-3 bg-white p-2 border rounded font-mono text-xs break-all text-gray-600">
                  Token: {p.credential_data}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
