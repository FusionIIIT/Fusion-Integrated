import { useState } from "react";

import { useReport } from "../api/hooks";

const reportTypes = ["visits", "inventory", "ambulance", "reimbursements", "demographics"];

function hasRows(data: Record<string, unknown>) {
  return Object.values(data).some((value) => {
    if (typeof value === "number") return value > 0;
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === "object" && value !== null) return Object.keys(value).length > 0;
    return false;
  });
}

export default function ReportsPage() {
  const [reportType, setReportType] = useState("visits");
  const report = useReport(reportType);
  return <main>
    <h1>PHC aggregate reports</h1>
    <label htmlFor="report-type">Report category</label>
    <select id="report-type" value={reportType}
      onChange={(event) => setReportType(event.target.value)}>
      {reportTypes.map((type) => <option key={type} value={type}>{type}</option>)}
    </select>
    {report.isPending && <p role="status">Loading report…</p>}
    {report.isError && <p role="alert">{report.error instanceof Error
      ? report.error.message : "The report could not be loaded."}</p>}
    {report.data && !hasRows(report.data.data) && <p>No data is available for this report.</p>}
    {report.data && <pre aria-label="Aggregate report data">
      {JSON.stringify(report.data.data, null, 2)}
    </pre>}
  </main>;
}
