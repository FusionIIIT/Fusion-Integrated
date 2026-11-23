import { Select } from "@mantine/core";
import { useState } from "react";

import { usePeople } from "../api/hooks";

interface Option { value: string; label: string }

// A searchable person field; the IAM matches usernames and is asked only after two letters.
export function PersonPicker({ label, value, onChange, kind, required, name }: {
  label: string;
  value: number | null;
  onChange: (id: number | null, name: string) => void;
  kind?: string;
  required?: boolean;
  name?: string;
}) {
  const [query, setQuery] = useState("");
  const [chosen, setChosen] = useState<Option | null>(
    value != null && name ? { value: String(value), label: name } : null);
  const people = usePeople(query, kind);
  const found = (people.data ?? []).map((p) => ({
    value: String(p.user_id), label: `${p.display_name} (${p.kind})`,
  }));
  // The server already matched; keep the chosen person listed after the search moves on.
  const options = chosen && !found.some((o) => o.value === chosen.value)
    ? [chosen, ...found] : found;
  return (
    <Select
      label={label} searchable required={required} clearable
      placeholder="Type at least two letters of a username"
      data={options} value={value != null ? String(value) : null}
      filter={({ options: all }) => all}
      searchValue={query} onSearchChange={setQuery}
      nothingFoundMessage={query.trim().length < 2 ? "Keep typing" : "Nobody found"}
      onChange={(v) => {
        const picked = options.find((o) => o.value === v) ?? null;
        setChosen(picked);
        onChange(v ? Number(v) : null, picked?.label ?? "");
      }}
    />
  );
}
