import { useState } from "react";
import {
  useDecideRequisition,
  useFulfillRequisition,
  useInventoryItems,
  useProcurementRequisitions,
  useSubmitRequisition,
} from "../api/hooks";
import type { ProcurementRequisition } from "../api/types";

export default function ProcurementRequisitionsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedReq, setSelectedReq] = useState<ProcurementRequisition | null>(null);
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [decisionType, setDecisionType] = useState<"approve" | "reject">("approve");
  const [decisionRemarks, setDecisionRemarks] = useState("");

  const { data: requisitions, isLoading, error } = useProcurementRequisitions(statusFilter || undefined);
  const { data: inventoryItems } = useInventoryItems();

  const submitRequisition = useSubmitRequisition();
  const decideRequisition = useDecideRequisition();
  const fulfillRequisition = useFulfillRequisition();

  // Create requisition form state
  const [justification, setJustification] = useState("");
  const [items, setItems] = useState<{ item_id: number; quantity: number }[]>([
    { item_id: 0, quantity: 1 },
  ]);
  const [createError, setCreateError] = useState("");

  const handleAddItemRow = () => {
    setItems([...items, { item_id: 0, quantity: 1 }]);
  };

  const handleRemoveItemRow = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleItemChange = (index: number, field: "item_id" | "quantity", val: number) => {
    const updated = [...items];
    if (field === "item_id") {
      updated[index] = { item_id: val, quantity: updated[index]?.quantity ?? 1 };
    } else {
      updated[index] = { item_id: updated[index]?.item_id ?? 0, quantity: val };
    }
    setItems(updated);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError("");
    const validItems = items.filter((it) => it.item_id > 0 && it.quantity > 0);
    if (!validItems.length) {
      setCreateError("Please select at least one valid item with quantity > 0.");
      return;
    }
    if (!justification.trim()) {
      setCreateError("Please provide a procurement justification.");
      return;
    }

    try {
      await submitRequisition.mutateAsync({
        justification,
        items: validItems,
      });
      setShowCreateModal(false);
      setJustification("");
      setItems([{ item_id: 0, quantity: 1 }]);
    } catch (err: any) {
      setCreateError(err.response?.data?.error || err.message || "Failed to submit requisition");
    }
  };

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedReq) return;
    try {
      await decideRequisition.mutateAsync({
        reqId: selectedReq.id,
        decision: decisionType,
        remarks: decisionRemarks,
      });
      setDecisionModalOpen(false);
      setSelectedReq(null);
      setDecisionRemarks("");
    } catch (err: any) {
      alert(err.response?.data?.error || err.message || "Decision submission failed");
    }
  };

  const handleFulfill = async (reqId: number) => {
    if (!confirm("Are you sure you want to mark this requisition as Fulfilled? Note: Received stock must be added separately via Stock Adjustment once inspected.")) {
      return;
    }
    try {
      await fulfillRequisition.mutateAsync(reqId);
    } catch (err: any) {
      alert(err.response?.data?.error || err.message || "Failed to mark fulfilled");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "Pending Approval":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">Pending Approval</span>;
      case "Approved":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">Approved</span>;
      case "Rejected":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">Rejected</span>;
      case "Fulfilled":
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800">Fulfilled</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800">{status}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Procurement Requisitions</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage PHC medical supplies indenting, administrative approval, and vendor delivery fulfillment.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
          >
            Create New Requisition
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2">
        {["", "Pending Approval", "Approved", "Fulfilled", "Rejected"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              statusFilter === st
                ? "bg-indigo-600 text-white"
                : "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50"
            }`}
          >
            {st || "All Requisitions"}
          </button>
        ))}
      </div>

      {/* Requisitions List */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Loading requisitions...</div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          Failed to load procurement requisitions.
        </div>
      ) : !requisitions?.length ? (
        <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-500">
          No requisitions found matching the selected status.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {requisitions.map((req) => (
            <div key={req.id} className="bg-white border border-slate-200 rounded-lg shadow-sm p-5 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-slate-900 text-base">{req.requisition_number}</span>
                  {getStatusBadge(req.status)}
                </div>
                <div className="text-xs text-slate-500">
                  Requested on {new Date(req.created_at).toLocaleDateString()}
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Justification</p>
                <p className="text-sm text-slate-700 mt-0.5">{req.justification}</p>
              </div>

              {/* Items List */}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Requested Supplies</p>
                <div className="border border-slate-200 rounded-md overflow-hidden">
                  <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                    <thead className="bg-slate-50 text-slate-600 font-medium">
                      <tr>
                        <th className="px-3 py-2">Item Code</th>
                        <th className="px-3 py-2">Item Name</th>
                        <th className="px-3 py-2">Quantity</th>
                        <th className="px-3 py-2">Unit</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {req.items.map((it) => (
                        <tr key={it.id}>
                          <td className="px-3 py-2 font-mono">{it.item_code}</td>
                          <td className="px-3 py-2 font-medium">{it.item_name}</td>
                          <td className="px-3 py-2">{it.quantity_requested}</td>
                          <td className="px-3 py-2">{it.unit}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Decision / Fulfilled info */}
              {(req.decision_at || req.fulfilled_at) && (
                <div className="bg-slate-50 p-3 rounded text-xs space-y-1 text-slate-600">
                  {req.decision_at && (
                    <div>
                      <span className="font-medium">Decision ({req.status}):</span> at {new Date(req.decision_at).toLocaleString()}
                      {req.decision_remarks && ` - Remarks: ${req.decision_remarks}`}
                    </div>
                  )}
                  {req.fulfilled_at && (
                    <div>
                      <span className="font-medium">Fulfilled:</span> at {new Date(req.fulfilled_at).toLocaleString()}
                    </div>
                  )}
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-slate-100">
                {req.status === "Pending Approval" && (
                  <>
                    <button
                      onClick={() => {
                        setSelectedReq(req);
                        setDecisionType("approve");
                        setDecisionModalOpen(true);
                      }}
                      className="px-3 py-1.5 text-xs font-medium rounded text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-300"
                    >
                      Approve Requisition
                    </button>
                    <button
                      onClick={() => {
                        setSelectedReq(req);
                        setDecisionType("reject");
                        setDecisionModalOpen(true);
                      }}
                      className="px-3 py-1.5 text-xs font-medium rounded text-red-700 bg-red-50 hover:bg-red-100 border border-red-300"
                    >
                      Reject Requisition
                    </button>
                  </>
                )}

                {req.status === "Approved" && (
                  <button
                    onClick={() => handleFulfill(req.id)}
                    className="px-3 py-1.5 text-xs font-medium rounded text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-300"
                  >
                    Mark as Fulfilled
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Requisition Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 border-b pb-2">Create Procurement Indent</h2>
            {createError && (
              <div className="p-3 bg-red-50 text-red-700 rounded text-xs border border-red-200">
                {createError}
              </div>
            )}
            <form onSubmit={handleCreateSubmit} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Procurement Justification <span className="text-red-500">*</span>
                </label>
                <textarea
                  required
                  rows={2}
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  placeholder="State the requirement reason (e.g. Low seasonal buffer stock of paracetamol)..."
                  className="w-full border border-slate-300 rounded p-2 text-xs focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-medium text-slate-700">Supplies List</label>
                  <button
                    type="button"
                    onClick={handleAddItemRow}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    + Add Item
                  </button>
                </div>
                <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                  {items.map((it, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <select
                        value={it.item_id}
                        onChange={(e) => handleItemChange(idx, "item_id", Number(e.target.value))}
                        className="flex-1 border border-slate-300 rounded p-2 text-xs focus:ring-indigo-500 focus:border-indigo-500"
                      >
                        <option value={0}>-- Select Catalog Item --</option>
                        {inventoryItems?.map((inv) => (
                          <option key={inv.id} value={inv.id}>
                            {inv.name} ({inv.item_code}) - Curr: {inv.stock_level} {inv.unit}
                          </option>
                        ))}
                      </select>
                      <input
                        type="number"
                        min="1"
                        value={it.quantity}
                        onChange={(e) => handleItemChange(idx, "quantity", Number(e.target.value))}
                        className="w-24 border border-slate-300 rounded p-2 text-xs focus:ring-indigo-500 focus:border-indigo-500"
                        placeholder="Qty"
                      />
                      {items.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveItemRow(idx)}
                          className="text-red-500 hover:text-red-700 p-1 text-xs"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-300 rounded text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitRequisition.isPending}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-medium disabled:opacity-50"
                >
                  {submitRequisition.isPending ? "Submitting..." : "Submit Requisition"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Decision Modal */}
      {decisionModalOpen && selectedReq && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6 space-y-4">
            <h2 className="text-lg font-bold text-slate-900 border-b pb-2">
              {decisionType === "approve" ? "Approve Requisition" : "Reject Requisition"}
            </h2>
            <p className="text-xs text-slate-600">
              Requisition: <span className="font-mono font-semibold">{selectedReq.requisition_number}</span>
            </p>
            <form onSubmit={handleDecisionSubmit} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Decision Remarks
                </label>
                <textarea
                  rows={3}
                  value={decisionRemarks}
                  onChange={(e) => setDecisionRemarks(e.target.value)}
                  placeholder="Enter approval conditions or rejection reasons..."
                  className="w-full border border-slate-300 rounded p-2 text-xs focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => setDecisionModalOpen(false)}
                  className="px-4 py-2 border border-slate-300 rounded text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={decideRequisition.isPending}
                  className={`px-4 py-2 text-white rounded text-xs font-medium disabled:opacity-50 ${
                    decisionType === "approve" ? "bg-emerald-600 hover:bg-emerald-700" : "bg-red-600 hover:bg-red-700"
                  }`}
                >
                  {decideRequisition.isPending ? "Processing..." : `Confirm ${decisionType === "approve" ? "Approval" : "Rejection"}`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
