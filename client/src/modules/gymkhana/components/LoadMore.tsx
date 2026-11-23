import { Button, Center } from "@mantine/core";

export function LoadMore({ list }: {
  list: { hasMore: boolean; loadMore: () => void; loadingMore: boolean };
}) {
  if (!list.hasMore) return null;
  return (
    <Center mt="md">
      <Button variant="default" onClick={list.loadMore} loading={list.loadingMore}>
        Load more
      </Button>
    </Center>
  );
}
