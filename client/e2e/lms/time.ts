export function localTime(afterSeconds: number, baseTime = Date.now()) {
  const date = new Date(baseTime + afterSeconds * 1000);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 19);
  return local.replace(/:00$/, "");
}
