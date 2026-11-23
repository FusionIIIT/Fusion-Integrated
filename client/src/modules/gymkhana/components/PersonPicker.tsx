import { useState } from "react";
import { Select } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";

import { errorMessage } from "../../../lib/http";
import { usePeople } from "../api/hooks";
import type { PersonKind } from "../api/types";

/** Search by username; the value is the person's id. */
export function PersonPicker({ label, kind, value, onChange }: {
  label: string;
  kind: PersonKind;
  value: number | null;
  onChange: (id: number | null) => void;
}) {
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<{ value: string; label: string } | null>(null);
  const [typed] = useDebouncedValue(search.trim(), 250);
  const term = picked && typed === picked.label ? "" : typed;
  const { data, isFetching, error } = usePeople(term, kind);

  const found = (data ?? []).map((p) => ({
    value: String(p.user_id), label: `${p.display_name} (${p.username})`,
  }));
  const options = picked && !found.some((o) => o.value === picked.value)
    ? [picked, ...found] : found;

  return (
    <Select
      label={label} required searchable clearable
      placeholder="Type a username, such as stu00001"
      data={options}
      filter={({ options: all }) => all}
      value={value === null ? null : String(value)}
      onChange={(next) => {
        setPicked(options.find((o) => o.value === next) ?? null);
        onChange(next === null ? null : Number(next));
      }}
      searchValue={search} onSearchChange={setSearch}
      error={error ? errorMessage(error) : undefined}
      nothingFoundMessage={isFetching ? "Searching…"
        : term.length < 3 ? "Type at least 3 characters" : `No ${kind} found`}
    />
  );
}
