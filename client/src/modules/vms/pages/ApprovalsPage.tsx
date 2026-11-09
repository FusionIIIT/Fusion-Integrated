import VmsPage from "./VmsPage";

export default function ApprovalsPage() {
  return (
    <VmsPage
      title="Approvals"
      description="Visit requests waiting for your decision."
      endpoints={["host/requests", "host/requests/{id}/decision", "extensions"]}
    />
  );
}
