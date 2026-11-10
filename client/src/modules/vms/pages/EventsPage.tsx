import VmsPage from "./VmsPage";

export default function EventsPage() {
  return (
    <VmsPage
      title="Events"
      description="Event batches and attendance."
      endpoints={["events", "events/{id}/attendees"]}
    />
  );
}
