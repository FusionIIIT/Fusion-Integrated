import React, { useState } from "react";
import { PreRegisterForm } from "./components/PreRegisterForm";
import { HostApprovalsView } from "./components/HostApprovalsView";
import { GateControlView } from "./components/GateControlView";
import { ActivePassesView } from "./components/ActivePassesView";

export const VmsPage: React.FC = () => {
  const [tab, setTab] = useState<"register" | "approvals" | "gate" | "passes">("register");

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6 flex justify-between items-center border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Visitor Management System (VMS)</h1>
          <p className="text-sm text-gray-500">Campus Visitor Pre-Registration, Host Authorizations & Gate Pass Validation</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setTab("register")}
            className={`px-3 py-1.5 rounded text-sm font-medium ${tab === "register" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}
          >
            Pre-Register
          </button>
          <button
            onClick={() => setTab("approvals")}
            className={`px-3 py-1.5 rounded text-sm font-medium ${tab === "approvals" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}
          >
            Host Queue
          </button>
          <button
            onClick={() => setTab("gate")}
            className={`px-3 py-1.5 rounded text-sm font-medium ${tab === "gate" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}
          >
            Gate Scanner
          </button>
          <button
            onClick={() => setTab("passes")}
            className={`px-3 py-1.5 rounded text-sm font-medium ${tab === "passes" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-700"}`}
          >
            Roster & Passes
          </button>
        </div>
      </div>

      {tab === "register" && <PreRegisterForm />}
      {tab === "approvals" && <HostApprovalsView />}
      {tab === "gate" && <GateControlView />}
      {tab === "passes" && <ActivePassesView />}
    </div>
  );
};

export default VmsPage;
