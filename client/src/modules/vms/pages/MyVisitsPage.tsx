import VmsPage from "./VmsPage";

export default function MyVisitsPage() {
  return (
    <VmsPage
      title="My Visits"
      description="Visits you host and their current status."
      endpoints={["visit/passes", "notify/inbox"]}
    />
  );
}
