import VmsPage from "./VmsPage";

export default function GatePage() {
  return (
    <VmsPage
      title="Gate"
      description="Validate, check in and check out visitors at the gate."
      endpoints={["gate/validate", "visit/check-out", "gate/override"]}
    />
  );
}
