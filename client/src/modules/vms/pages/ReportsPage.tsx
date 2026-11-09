import VmsPage from "./VmsPage";

export default function ReportsPage() {
  return (
    <VmsPage
      title="Reports"
      description="Anonymised visitor reports and exports."
      endpoints={["reports", "reports/{key}", "reports/{key}/export"]}
    />
  );
}
