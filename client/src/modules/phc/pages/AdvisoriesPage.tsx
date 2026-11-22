import { useState, type FormEvent } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { useAdvisories, usePublishAdvisory } from "../api/hooks";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";

export default function AdvisoriesPage() {
  const { can } = useAuth();
  const advisories = useAdvisories();
  const publish = usePublishAdvisory();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    publish.mutate({ title, body });
  }

  return <ResourcePanel title="Health advisories" data={advisories.data}
    isPending={advisories.isPending} isError={advisories.isError} error={advisories.error}
    emptyText="There are no published health advisories."
    renderRow={(advisory) => <article>
      <h2>{advisory.title}</h2>
      <p>{advisory.body}</p>
      {advisory.published_at && <time dateTime={advisory.published_at}>
        {new Date(advisory.published_at).toLocaleString()}
      </time>}
    </article>}>
    {can("phc.advisory.publish") && <form onSubmit={submit}>
      <h2>Publish a health advisory</h2>
      <label htmlFor="advisory-title">Title</label>
      <input id="advisory-title" required value={title}
        onChange={(event) => setTitle(event.target.value)} />
      <label htmlFor="advisory-body">Advisory</label>
      <textarea id="advisory-body" required value={body}
        onChange={(event) => setBody(event.target.value)} />
      <button type="submit" disabled={publish.isPending}>Publish advisory</button>
      <MutationMessage isPending={publish.isPending} isError={publish.isError}
        error={publish.error} isSuccess={publish.isSuccess} />
    </form>}
  </ResourcePanel>;
}
