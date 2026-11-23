import { Button, Loader, Text } from "@mantine/core";

import { ErrorState } from "../../ui/components/ErrorState";

export function FeedState({ query, empty }: {
  query: {
    isPending: boolean; isError: boolean; isSuccess: boolean; hasNextPage: boolean;
    isFetchingNextPage: boolean; error: unknown; rows: unknown[]; fetchNextPage: () => unknown;
  };
  empty: string;
}) {
  if (query.isPending) return <Loader aria-label="Loading" />;
  if (query.isError) return <ErrorState error={query.error} />;
  if (query.isSuccess && query.rows.length === 0) return <Text c="dimmed">{empty}</Text>;
  if (!query.hasNextPage) return null;
  return (
    <Button variant="default" loading={query.isFetchingNextPage}
      onClick={() => void query.fetchNextPage()}>
      Load more
    </Button>
  );
}
