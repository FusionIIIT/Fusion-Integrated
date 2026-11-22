import { Button, Group, Paper, Stack, TagsInput, Text, Textarea } from "@mantine/core";
import { useState } from "react";

import { ErrorState } from "../../ui/components/ErrorState";
import { useDepartmentAction, useDepartmentFeed } from "./api";
import { FeedState } from "./FeedState";

interface EditValues {
  content: string;
  target_roles: string[];
  target_programmes: string[];
  target_batch_years: number[];
}
interface ManagedAnnouncement extends EditValues { id: number }

function AnnouncementForm({ initial, onClose }: { initial?: ManagedAnnouncement; onClose: () => void }) {
  const [content, setContent] = useState(initial?.content ?? "");
  const [roles, setRoles] = useState(initial?.target_roles ?? []);
  const [programmes, setProgrammes] = useState(initial?.target_programmes ?? []);
  const [years, setYears] = useState(initial?.target_batch_years.map(String) ?? []);
  const action = useDepartmentAction();
  const validYears = years.every((year) => /^\d{4}$/.test(year) && Number(year) >= 1900 && Number(year) <= 2200);

  return (
    <Paper withBorder p="md" component="form" onSubmit={(event) => {
      event.preventDefault();
      if (!validYears || !content.trim()) return;
      const values = { content, target_roles: roles, target_programmes: programmes, target_batch_years: years.map(Number) };
      action.mutate(initial
        ? { path: `announcements/${initial.id}/action`, data: { action: "edit", announcement: values } }
        : { path: "announcements", data: values }, { onSuccess: onClose });
    }}>
      <Stack>
        <Textarea label="Announcement" required maxLength={8000} value={content}
          onChange={(event) => setContent(event.currentTarget.value)} />
        <Text size="sm" c="dimmed">An empty target field includes everyone in your department for that field.</Text>
        <TagsInput label="Target roles" description="Use IAM role names such as student or faculty."
          value={roles} onChange={setRoles} maxTags={20} />
        <TagsInput label="Target programmes" value={programmes} onChange={setProgrammes} maxTags={20} />
        <TagsInput label="Target batch years" value={years} onChange={setYears} maxTags={20}
          error={!validYears && "Enter four-digit years from 1900 to 2200."} />
        <Group>
          <Button type="submit" loading={action.isPending} disabled={!content.trim() || !validYears}>
            {initial ? "Save changes" : "Publish"}
          </Button>
          <Button variant="default" onClick={onClose}>Cancel</Button>
        </Group>
        {action.isError && <ErrorState error={action.error} />}
      </Stack>
    </Paper>
  );
}

export function PublishAnnouncement() {
  const [editing, setEditing] = useState(false);
  return editing
    ? <AnnouncementForm onClose={() => setEditing(false)} />
    : <Button onClick={() => setEditing(true)}>New announcement</Button>;
}

export function ManageAnnouncements() {
  const feed = useDepartmentFeed<ManagedAnnouncement>("announcements/managed");
  const action = useDepartmentAction();
  const [editing, setEditing] = useState<number | null>(null);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  function run(id: number, decision: "hide" | "delete") {
    action.mutate({ path: `announcements/${id}/action`, data: { action: decision } }, {
      onSuccess: () => setDeleteId(null),
    });
  }

  return (
    <Stack>
      <Text fw={600}>Manage active announcements</Text>
      {feed.rows.map((row) => editing === row.id
        ? <AnnouncementForm key={row.id} initial={row} onClose={() => setEditing(null)} />
        : (
          <Paper key={row.id} p="md" withBorder>
            <Stack>
              <Text style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{row.content}</Text>
              {deleteId === row.id ? (
                <Group>
                  <Text>Delete this announcement?</Text>
                  <Button color="red" loading={action.isPending} onClick={() => run(row.id, "delete")}>Delete</Button>
                  <Button variant="default" onClick={() => setDeleteId(null)}>Cancel</Button>
                </Group>
              ) : (
                <Group>
                  <Button variant="default" onClick={() => setEditing(row.id)}>Edit</Button>
                  <Button variant="default" disabled={action.isPending} onClick={() => run(row.id, "hide")}>Hide</Button>
                  <Button color="red" variant="subtle" onClick={() => setDeleteId(row.id)}>Delete</Button>
                </Group>
              )}
            </Stack>
          </Paper>
        ))}
      {action.isError && <ErrorState error={action.error} />}
      <FeedState query={feed} empty="There are no active announcements to manage." />
    </Stack>
  );
}
