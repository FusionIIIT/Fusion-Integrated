import { useNotifications } from "../api/hooks";
import { ResourcePanel } from "../components/ResourcePanel";

export default function NotificationsPage() {
  const query = useNotifications();
  return <ResourcePanel title="PHC notifications" data={query.data}
    isPending={query.isPending} isError={query.isError} error={query.error}
    emptyText="You have no PHC notifications."
    renderRow={(notification) => <article>
      <h2>{notification.event_type.replaceAll("_", " ")}</h2>
      <time dateTime={notification.created_at}>
        {new Date(notification.created_at).toLocaleString()}
      </time>
      <p>{notification.message}</p>
    </article>} />;
}
