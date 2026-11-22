import React, { useEffect, useState } from "react";
import { iwdApi } from "../api";
import type { Complaint } from "../api/types";

export const ComplaintsPage: React.FC = () => {
  const [complaints, setComplaints] = useState<Complaint[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState<"civil" | "electrical">("civil");
  const [location, setLocation] = useState("");
  const [urgency, setUrgency] = useState<"low" | "medium" | "high" | "emergency">("medium");
  const [remarks, setRemarks] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchComplaints = async () => {
    try {
      const data = await iwdApi.listComplaints();
      setComplaints(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComplaints();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await iwdApi.createComplaint({ category, location, urgency, remarks });
      setLocation("");
      setRemarks("");
      await fetchComplaints();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Institute Work Department — Maintenance Complaints</h1>

      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h2 className="text-lg font-semibold mb-4">Submit Maintenance Complaint</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Category</label>
              <select
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"
                value={category}
                onChange={(e) => setCategory(e.target.value as "civil" | "electrical")}
              >
                <option value="civil">Civil Maintenance</option>
                <option value="electrical">Electrical Maintenance</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Urgency</label>
              <select
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"
                value={urgency}
                onChange={(e) => setUrgency(e.target.value as any)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="emergency">Emergency</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Location</label>
              <input
                type="text"
                required
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"
                placeholder="e.g. Hall 4, Room 102"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Remarks</label>
            <textarea
              className="mt-1 block w-full rounded-md border-gray-300 shadow-sm p-2 border"
              rows={2}
              placeholder="Describe the maintenance issue..."
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? "Submitting..." : "Submit Complaint"}
          </button>
        </form>
      </div>

      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h2 className="text-lg font-semibold mb-4">My Complaints</h2>
        {loading ? (
          <p className="text-gray-500">Loading complaints...</p>
        ) : complaints.length === 0 ? (
          <p className="text-gray-500">No complaints submitted yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Complaint ID</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Location</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Urgency</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {complaints.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-2 text-sm font-medium text-gray-900">{c.complaint_id}</td>
                    <td className="px-4 py-2 text-sm text-gray-500 capitalize">{c.category}</td>
                    <td className="px-4 py-2 text-sm text-gray-500">{c.location}</td>
                    <td className="px-4 py-2 text-sm text-gray-500 capitalize">{c.urgency}</td>
                    <td className="px-4 py-2 text-sm">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                        {c.status}
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
