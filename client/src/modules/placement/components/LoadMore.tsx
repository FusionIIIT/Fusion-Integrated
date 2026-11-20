import { Button, Center } from "@mantine/core";

/** Loads the next page of a cursor list; renders nothing once every row is shown. */
export function LoadMore({ list }: {
  list: { hasNextPage?: boolean; isFetchingNextPage?: boolean; fetchNextPage?: () => unknown };
}) {
  if (!list.hasNextPage || !list.fetchNextPage) return null;
  return (
    <Center mt="md">
      <Button variant="default" size="xs" loading={list.isFetchingNextPage}
        onClick={() => list.fetchNextPage?.()}>
        Load more
      </Button>
    </Center>
  );
}
