import { useState } from "react";
import { usePHCReport } from "../api/hooks";

export default function PHCReportsPage() {
  const [reportType, setReportType] = useState<"demographics" | "service_utilization" | "inventory">(
    "service_utilization"
  );

  const { data: reportData, isLoading, error } = usePHCReport(reportType);

  const handleExportCSV = () => {
    if (!reportData) return;
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
      JSON.stringify(reportData, null, 2)
    )}`;
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", jsonString);
    downloadAnchor.setAttribute("download", `phc_report_${reportType}_${new Date().toISOString().slice(0, 10)}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">PHC Operational & Clinical Reports</h1>
          <p className="text-sm text-slate-500 mt-1">
            Aggregated institutional analytics and epidemiology metrics with strict patient PII de-identification (BR-12).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => window.print()}
            className="px-3.5 py-2 border border-slate-300 rounded-md text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 shadow-sm"
          >
            Print Report
          </button>
          <button
            onClick={handleExportCSV}
            disabled={!reportData}
            className="px-3.5 py-2 border border-transparent rounded-md text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm disabled:opacity-50"
          >
            Export Data
          </button>
        </div>
      </div>

      {/* Compliance Notice */}
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-md flex items-center justify-between text-xs text-blue-800">
        <div className="flex items-center gap-2">
          <span className="font-bold">Privacy Compliance (PHC-BR-12):</span>
          <span>All individual patient names, roll numbers, and personal identifiers have been de-identified in aggregated outputs.</span>
        </div>
        <span className="text-[11px] bg-blue-200/60 px-2 py-0.5 rounded font-mono font-medium">PII Stripped</span>
      </div>

      {/* Report Category Switcher */}
      <div className="flex border-b border-slate-200 space-x-6 text-sm">
        <button
          onClick={() => setReportType("service_utilization")}
          className={`pb-3 font-medium border-b-2 transition-colors ${
            reportType === "service_utilization"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          Campus Healthcare Utilization
        </button>
        <button
          onClick={() => setReportType("demographics")}
          className={`pb-3 font-medium border-b-2 transition-colors ${
            reportType === "demographics"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          Morbidity & Symptom Trends
        </button>
        <button
          onClick={() => setReportType("inventory")}
          className={`pb-3 font-medium border-b-2 transition-colors ${
            reportType === "inventory"
              ? "border-indigo-600 text-indigo-600"
              : "border-transparent text-slate-500 hover:text-slate-800"
          }`}
        >
          Dispensary & Inventory Buffer
        </button>
      </div>

      {/* Report Content */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Generating analytics metrics...</div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          Failed to generate PHC report.
        </div>
      ) : !reportData ? (
        <div className="p-8 text-center text-slate-400">No data returned for this query.</div>
      ) : (
        <div className="space-y-6">
          {/* Service Utilization View */}
          {reportType === "service_utilization" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Consultations</p>
                  <p className="text-3xl font-bold text-indigo-600 mt-2">{reportData.total_consultations ?? 0}</p>
                  <p className="text-xs text-slate-400 mt-1">Recorded outpatient visits</p>
                </div>
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Emergency Dispatches</p>
                  <p className="text-3xl font-bold text-amber-600 mt-2">{reportData.total_ambulance_trips ?? 0}</p>
                  <p className="text-xs text-slate-400 mt-1">Hospital ambulance transfers</p>
                </div>
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Medical Officers</p>
                  <p className="text-3xl font-bold text-emerald-600 mt-2">{reportData.active_doctors_count ?? 0}</p>
                  <p className="text-xs text-slate-400 mt-1">Resident & visiting doctors</p>
                </div>
              </div>
            </div>
          )}

          {/* Morbidity & Diagnosis View */}
          {reportType === "demographics" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-900 mb-4">Morbidity Diagnostics (Top Observed Diagnoses)</h3>
                  {reportData.top_diagnoses && Object.keys(reportData.top_diagnoses).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(reportData.top_diagnoses).map(([diag, count]: any) => (
                        <div key={diag} className="flex items-center justify-between border-b border-slate-100 pb-2 text-xs">
                          <span className="font-medium text-slate-700">{diag}</span>
                          <span className="px-2 py-0.5 rounded bg-slate-100 font-semibold text-slate-800">{count} cases</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No diagnostic data aggregated.</p>
                  )}
                </div>

                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <h3 className="text-sm font-semibold text-slate-900 mb-4">Common Symptom Classifications</h3>
                  {reportData.top_symptoms && Object.keys(reportData.top_symptoms).length > 0 ? (
                    <div className="space-y-2">
                      {Object.entries(reportData.top_symptoms).map(([symp, count]: any) => (
                        <div key={symp} className="flex items-center justify-between border-b border-slate-100 pb-2 text-xs">
                          <span className="font-medium text-slate-700">{symp}</span>
                          <span className="px-2 py-0.5 rounded bg-slate-100 font-semibold text-slate-800">{count} reports</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">No symptom data aggregated.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Inventory View */}
          {reportType === "inventory" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Catalog Items</p>
                  <p className="text-3xl font-bold text-slate-900 mt-2">{reportData.total_items_count ?? 0}</p>
                  <p className="text-xs text-slate-400 mt-1">Formulary medicines & consumables</p>
                </div>
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Stock Deficits (Below Buffer)</p>
                  <p className="text-3xl font-bold text-red-600 mt-2">{reportData.low_stock_count ?? 0}</p>
                  <p className="text-xs text-slate-400 mt-1">Items at or below reorder threshold</p>
                </div>
                <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pending Indents</p>
                  <p className="text-3xl font-bold text-amber-600 mt-2">{reportData.pending_requisitions_count ?? 0}</p>
                  <p className="text-xs text-slate-400 mt-1">Requisitions awaiting approval</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
