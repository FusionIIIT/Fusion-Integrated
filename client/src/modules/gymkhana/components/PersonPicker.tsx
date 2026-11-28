import { useState } from "react";
import { Select } from "@mantine/core";

import { usePeople } from "../api/hooks";

interface Option { value: string; label: string }

/** Type at least two characters of a username; the server returns only that kind of person. */
export function PersonPicker({ label, kind, value, onChange, required, initialLabel }: {
  label: string;
  kind: "student" | "faculty";
  value: number | null;
  onChange: (id: number | null) => void;
  required?: boolean;
  initialLabel?: string;
}) {
  const [picked, setPicked] = useState<Option | null>(
    value !== null ? { value: String(value), label: initialLabel || `User ${value}` } : null);
  const [search, setSearch] = useState(picked?.label ?? "");
  // The box shows the chosen person's label after a pick; that text is not a new search.
  const query = search === picked?.label ? "" : search;
  const { data, isFetching, error } = usePeople(query, kind);
  const found = (data ?? []).map((p) => ({
    value: String(p.user_id), label: `${p.display_name} (${p.username})` }));
  const options = picked && !found.some((o) => o.value === picked.value)
    ? [picked, ...found] : found;

  return (
    <Select
      label={label}
      required={required}
      searchable
      clearable
      // Picking the person already chosen keeps them; only the clear button empties the field.
      allowDeselect={false}
      data={options}
      value={value === null ? null : String(value)}
      searchValue={search}
      onSearchChange={setSearch}
      onChange={(v, option) => {
        setPicked(v ? { value: v, label: option.label } : null);
        onChange(v ? Number(v) : null);
      }}
      nothingFoundMessage={query.trim().length < 2 ? "Type at least two characters"
        : isFetching ? "Searching…" : "No one found"}
      error={error ? "Could not search the directory." : undefined}
      placeholder="Search by username"
    />
  );
}
