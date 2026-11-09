import VmsPage from "./VmsPage";

export default function RosterPage() {
  return (
    <VmsPage
      title="Roster"
      description="Live occupancy, on-site visitors and alerts."
      endpoints={["monitor/dashboard", "monitor/on-site", "monitor/movements"]}
    />
  );
}
