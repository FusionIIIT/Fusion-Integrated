import { Button, Group } from "@mantine/core";

import type { PagedList } from "../api/hooks";

// Fetches the next page of a list; renders nothing once every row is loaded.
export function LoadMore({ list }: { list: PagedList }) {
  if (!list.hasNextPage) return null;
  return (
    <Group justify="center" mt="md">
      <Button variant="default" loading={list.isFetchingNextPage}
        onClick={() => list.fetchNextPage()}>
        Load more
      </Button>
    </Group>
  );
}
