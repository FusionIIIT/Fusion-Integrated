import type { ReactNode } from "react";

import type { Page } from "../api/types";

export function ResourcePanel<T>({ title, data, isPending, isError, error,
  emptyText, children, renderRow }: {
  title: string;
  data: Page<T> | T[] | undefined;
  isPending: boolean;
  isError: boolean;
  error?: unknown;
  emptyText: string;
  children?: ReactNode;
  renderRow: (row: T, index: number) => ReactNode;
}) {
  if (isPending) return <main><h1>{title}</h1><p role="status">Loading {title.toLowerCase()}…</p></main>;
  if (isError) {
    const message = error instanceof Error ? error.message : "The PHC service could not load this information.";
    return <main><h1>{title}</h1><p role="alert">{message}</p></main>;
  }
  const rows = Array.isArray(data) ? data : data?.results ?? [];
  return (
    <main>
      <h1>{title}</h1>
      {children}
      {rows.length === 0 ? <p>{emptyText}</p> : (
        <ul aria-label={`${title} list`}>
          {rows.map((row, index) => <li key={index}>{renderRow(row, index)}</li>)}
        </ul>
      )}
    </main>
  );
}

export function MutationMessage({ isPending, isError, error, isSuccess }: {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  isSuccess: boolean;
}) {
  if (isPending) return <p role="status">Saving…</p>;
  if (isError) {
    const message = error instanceof Error ? error.message : "The PHC service could not save this change.";
    return <p role="alert">{message}</p>;
  }
  return isSuccess ? <p role="status">Saved.</p> : null;
}
