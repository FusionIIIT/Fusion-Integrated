import VmsPage from "./VmsPage";

export default function MusterPage() {
  return (
    <VmsPage
      title="Muster"
      description="Emergency muster roll call."
      endpoints={["muster", "muster/current", "muster/{id}"]}
    />
  );
}
