import { Alert, Button, Group, NativeSelect, Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";

import { errorMessage } from "../../../lib/http";
import { useCourses } from "../api/hooks";

export function Feedback({ error, success }: { error: unknown; success?: boolean }) {
  return <>{error != null && <Alert role="alert" color="red">{errorMessage(error)}</Alert>}
    {success && <Alert role="status" color="green">Saved successfully.</Alert>}</>;
}

export function Pending() { return <Text role="status">Loading course information…</Text>; }

export function CoursePicker({ selected, onSelect }: {
  selected: number | null; onSelect: (id: number | null) => void;
}) {
  const query = useCourses();
  if (query.error) return <Feedback error={query.error} />;
  if (query.isPending) return <Pending />;
  if (!query.items.length) return <Text>No linked courses are available for this acting role.</Text>;
  return <Stack>
    <NativeSelect label="Course" value={selected ?? ""}
      onChange={(event) => onSelect(event.currentTarget.value ? Number(event.currentTarget.value) : null)}
      data={[{ value: "", label: "Choose a course" }, ...query.items.map((course) => ({
        value: String(course.id), label: `${course.course_code} · ${course.course_name} · ${course.working_year ?? ""} ${course.session ?? ""}`,
      }))]} />
    {query.hasNextPage && <Button variant="subtle" onClick={() => void query.fetchNextPage()}
      loading={query.isFetchingNextPage}>Load more courses</Button>}
  </Stack>;
}

export function ListState({ pending, error, empty, more, onMore, children }: {
  pending: boolean; error: unknown; empty: boolean; more?: boolean;
  onMore?: () => void; children: ReactNode;
}) {
  if (error) return <Feedback error={error} />;
  if (pending) return <Pending />;
  return <Stack>{empty ? <Text>No items yet.</Text> : children}
    {more && <Group><Button onClick={onMore} variant="subtle">Load more items</Button></Group>}
  </Stack>;
}

export function utcValue(value: string): string { return value ? new Date(value).toISOString() : ""; }
export function localValue(value: string): string {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16);
}
