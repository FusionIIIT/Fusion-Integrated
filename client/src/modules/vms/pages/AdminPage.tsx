import VmsPage from "./VmsPage";

export default function AdminPage() {
  return (
    <VmsPage
      title="Administration"
      description="Policies, blacklist, safe-list, zones and roles."
      endpoints={["policies", "blacklist", "roles", "zones/elevations"]}
    />
  );
}
