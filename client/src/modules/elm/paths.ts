/** Keep cursor URLs on the configured Fusion HTTP client and API namespace. */
export function elmRequestPath(path: string): string {
  if (!path.startsWith("/") && !/^[a-z][a-z\d+.-]*:\/\//i.test(path)) {
    return `/elm/${path}`;
  }
  const cursor = new URL(path, "http://elm.invalid");
  const pathname = cursor.pathname.replace(/^\/api\/v1(?=\/)/, "");
  if (!pathname.startsWith("/elm/")) {
    throw new Error("The pagination link is outside Employee Leave Management.");
  }
  return pathname + cursor.search;
}
