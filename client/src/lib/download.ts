/** Saving a fetched file, so downloads stay inside the SPA.
 *
 *  A plain <a href> to an API path leaves the app: a 403, 429 or 500 replaces
 *  the whole page with the server's error output instead of a toast.
 */

/** Prefer the server's filename — it carries the export timestamp. */
export function filenameFromDisposition(
  header: unknown, fallback: string,
): string {
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(String(header ?? ""));
  if (!match?.[1]) return fallback;
  try {
    return decodeURIComponent(match[1]).replace(/[/\\]/g, "_").trim() || fallback;
  } catch {
    return fallback;
  }
}

export function saveBlob(data: Blob, filename: string): void {
  const url = URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoked on the next tick; Safari cancels the download if it goes too early.
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}
