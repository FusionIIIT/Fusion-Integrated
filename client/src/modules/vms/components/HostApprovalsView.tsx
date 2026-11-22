import React, { useEffect, useState } from "react";
import { fetchHostPending, decideVisitRequest } from "../api/client";
import { VisitRequest } from "../api/types";

export const HostApprovalsView: React.FC = () => {
  const [requests, setRequests] = useState<VisitRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const loadRequests = async () => {
    setLoading(true);
    try {
      const data = await fetchHostPending();
      setRequests(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRequests();
  }, []);

  const handleDecision = async (requestId: string, outcome: "APPROVE" | "REJECT") => {
    try {
      await decideVisitRequest(requestId, { outcome });
      await loadRequests();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-xl font-bold mb-4 text-gray-800">Pending Host Approvals</h3>
      {loading ? (
        <p className="text-gray-500">Loading requests...</p>
      ) : requests.length === 0 ? (
        <p className="text-gray-500">No pending approvals found.</p>
      ) : (
        <div className="divide-y divide-gray-200">
          {requests.map((r) => (
            <div key={r.request_id} className="py-4 flex justify-between items-center">
              <div>
                <p className="font-semibold text-lg">{r.visitor.full_name} ({r.visitor.organization || "Individual"})</p>
                <p className="text-sm text-gray-600">Purpose: {r.purpose}</p>
                <p className="text-xs text-gray-500">
                  Window: {new Date(r.scheduled_start_time).toLocaleString()} - {new Date(r.scheduled_end_time).toLocaleString()}
                </p>
                <p className="text-xs text-gray-400">Phone: {r.visitor.phone} | Doc: {r.visitor.id_document_number}</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleDecision(r.request_id, "APPROVE")}
                  className="bg-green-600 hover:bg-green-700 text-white text-sm font-medium py-1.5 px-3 rounded"
                >
                  Approve Pass
                </button>
                <button
                  onClick={() => handleDecision(r.request_id, "REJECT")}
                  className="bg-red-600 hover:bg-red-700 text-white text-sm font-medium py-1.5 px-3 rounded"
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
