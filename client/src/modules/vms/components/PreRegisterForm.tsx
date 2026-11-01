import React, { useState } from "react";
import { preRegisterVisit } from "../api/client";

export const PreRegisterForm: React.FC = () => {
  const [formData, setFormData] = useState({
    visitor_name: "",
    visitor_phone: "",
    visitor_email: "",
    id_doc_type: "AADHAAR",
    id_doc_number: "",
    organization: "",
    host_id: 101,
    purpose: "",
    scheduled_start: "",
    scheduled_end: "",
    remarks: "",
  });
  const [msg, setMsg] = useState<{ text: string; error?: boolean } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMsg(null);
    try {
      const res = await preRegisterVisit({
        ...formData,
        scheduled_start: new Date(formData.scheduled_start).toISOString(),
        scheduled_end: new Date(formData.scheduled_end).toISOString(),
      });
      setMsg({ text: `Pre-registration submitted successfully! Request ID: ${res.request_id}` });
    } catch (err: any) {
      setMsg({ text: err.message, error: true });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md max-w-2xl">
      <h3 className="text-xl font-bold mb-4 text-gray-800">VMS Pre-Register Visitor</h3>
      {msg && (
        <div className={`p-3 rounded mb-4 ${msg.error ? "bg-red-100 text-red-700" : "bg-green-100 text-green-700"}`}>
          {msg.text}
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Visitor Name</label>
            <input
              type="text"
              required
              value={formData.visitor_name}
              onChange={(e) => setFormData({ ...formData, visitor_name: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Phone</label>
            <input
              type="text"
              required
              value={formData.visitor_phone}
              onChange={(e) => setFormData({ ...formData, visitor_phone: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              required
              value={formData.visitor_email}
              onChange={(e) => setFormData({ ...formData, visitor_email: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">ID Document Type</label>
            <select
              value={formData.id_doc_type}
              onChange={(e) => setFormData({ ...formData, id_doc_type: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
            >
              <option value="AADHAAR">Aadhaar Card</option>
              <option value="PASSPORT">Passport</option>
              <option value="PAN">PAN Card</option>
              <option value="DRIVING_LICENSE">Driving License</option>
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">ID Document Number</label>
            <input
              type="text"
              required
              value={formData.id_doc_number}
              onChange={(e) => setFormData({ ...formData, id_doc_number: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Organization</label>
            <input
              type="text"
              value={formData.organization}
              onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Visit Purpose</label>
          <input
            type="text"
            required
            value={formData.purpose}
            onChange={(e) => setFormData({ ...formData, purpose: e.target.value })}
            className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Scheduled Start</label>
            <input
              type="datetime-local"
              required
              value={formData.scheduled_start}
              onChange={(e) => setFormData({ ...formData, scheduled_start: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Scheduled End</label>
            <input
              type="datetime-local"
              required
              value={formData.scheduled_end}
              onChange={(e) => setFormData({ ...formData, scheduled_end: e.target.value })}
              className="mt-1 block w-full border border-gray-300 rounded px-3 py-2"
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded transition"
        >
          {loading ? "Submitting..." : "Submit Pre-Registration"}
        </button>
      </form>
    </div>
  );
};
