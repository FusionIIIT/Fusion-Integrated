import React, { useState } from "react";
import { validateGateEntry, checkoutGateExit } from "../api/client";

export const GateControlView: React.FC = () => {
  const [credential, setCredential] = useState("");
  const [passId, setPassId] = useState("");
  const [gateId, setGateId] = useState("GATE-01");
  const [verdict, setVerdict] = useState<any>(null);
  const [checkoutMsg, setCheckoutMsg] = useState<string | null>(null);

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    setVerdict(null);
    const res = await validateGateEntry({ credential_data: credential, gate_id: gateId });
    setVerdict(res);
  };

  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    setCheckoutMsg(null);
    try {
      const res = await checkoutGateExit({ pass_id: passId, gate_id: gateId });
      setCheckoutMsg(`Checkout successful for Pass ${res.visitor_pass_id} at ${new Date(res.check_out_time).toLocaleTimeString()}`);
    } catch (err: any) {
      setCheckoutMsg(`Error: ${err.message}`);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* VMS-B-03 Check-in Scanner */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-bold mb-3 text-gray-800">Gate Entry Validation (Check-in)</h3>
        <form onSubmit={handleScan} className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-600">Gate ID</label>
            <input
              type="text"
              value={gateId}
              onChange={(e) => setGateId(e.target.value)}
              className="w-full border rounded px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-600">Credential Token / Pass QR</label>
            <input
              type="text"
              required
              value={credential}
              onChange={(e) => setCredential(e.target.value)}
              className="w-full border rounded px-3 py-1.5 text-sm"
              placeholder="Scan or paste credential data..."
            />
          </div>
          <button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 rounded">
            Verify Pass & Check-In
          </button>
        </form>

        {verdict && (
          <div className={`mt-4 p-4 rounded text-sm ${verdict.allowed ? "bg-green-50 border border-green-200 text-green-800" : "bg-red-50 border border-red-200 text-red-800"}`}>
            <p className="font-bold">{verdict.allowed ? "ACCESS GRANTED" : "ACCESS DENIED"}</p>
            <p>{verdict.reason}</p>
            {verdict.visitor_name && <p className="mt-1">Visitor: <strong>{verdict.visitor_name}</strong></p>}
            {verdict.pass_id && <p>Pass ID: {verdict.pass_id}</p>}
          </div>
        )}
      </div>

      {/* VMS-B-04 Checkout Terminal */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-bold mb-3 text-gray-800">Gate Departure (Check-out)</h3>
        <form onSubmit={handleCheckout} className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-600">Visitor Pass ID</label>
            <input
              type="text"
              required
              value={passId}
              onChange={(e) => setPassId(e.target.value)}
              className="w-full border rounded px-3 py-1.5 text-sm"
              placeholder="Enter Pass ID..."
            />
          </div>
          <button type="submit" className="w-full bg-slate-700 hover:bg-slate-800 text-white font-medium py-2 rounded">
            Record Departure & Complete Visit
          </button>
        </form>

        {checkoutMsg && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 text-blue-800 rounded text-sm">
            {checkoutMsg}
          </div>
        )}
      </div>
    </div>
  );
};
