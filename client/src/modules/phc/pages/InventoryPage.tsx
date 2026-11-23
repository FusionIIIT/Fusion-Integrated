import { useState, type FormEvent } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { useAdjustStock, useCreateInventoryItem, useInventory, useLowStockAlerts } from "../api/hooks";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";

export default function InventoryPage() {
  const { can } = useAuth();
  const inventory = useInventory();
  const alerts = useLowStockAlerts();
  const create = useCreateInventoryItem();
  const adjust = useAdjustStock();
  const [name, setName] = useState("");
  const [unit, setUnit] = useState("units");
  const [threshold, setThreshold] = useState("1");
  const [deltas, setDeltas] = useState<Record<number, string>>({});
  const [reasons, setReasons] = useState<Record<number, string>>({});

  function submitItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    create.mutate({ name, unit, reorder_threshold: Number(threshold) });
  }

  return <ResourcePanel title="PHC inventory" data={inventory.data}
    isPending={inventory.isPending || alerts.isPending}
    isError={inventory.isError || alerts.isError} error={inventory.error ?? alerts.error}
    emptyText="No inventory items are registered."
    renderRow={(item) => <article>
      <h2>{item.name}</h2>
      <p>Stock: {item.stock_quantity} {item.unit}; reorder threshold: {item.reorder_threshold}</p>
      {can("phc.inventory.update") && <form onSubmit={(event) => {
        event.preventDefault();
        adjust.mutate({ id: item.id, quantity_delta: Number(deltas[item.id]),
          reason: reasons[item.id] ?? "" });
      }}>
        <label htmlFor={`stock-delta-${item.id}`}>Stock adjustment for {item.name}</label>
        <input id={`stock-delta-${item.id}`} type="number" step="1" required
          value={deltas[item.id] ?? ""}
          onChange={(event) => setDeltas((current) => ({ ...current, [item.id]: event.target.value }))} />
        <label htmlFor={`stock-reason-${item.id}`}>Reason for {item.name}</label>
        <input id={`stock-reason-${item.id}`} value={reasons[item.id] ?? ""}
          onChange={(event) => setReasons((current) => ({ ...current, [item.id]: event.target.value }))} />
        <button type="submit" disabled={adjust.isPending}>Record stock movement</button>
      </form>}
    </article>}>
    {alerts.data?.results.length ? <section aria-label="Low stock alerts">
      <h2>Low stock alerts</h2>
      <ul>{alerts.data.results.map((alert) => <li key={alert.id}>
        {alert.item_name}: {alert.quantity_after} remaining; threshold {alert.reorder_threshold}
      </li>)}</ul>
    </section> : <p>No low stock alerts.</p>}
    {can("phc.inventory.create") && <form onSubmit={submitItem}>
      <h2>Add an inventory item</h2>
      <label htmlFor="inventory-name">Item name</label>
      <input id="inventory-name" required value={name}
        onChange={(event) => setName(event.target.value)} />
      <label htmlFor="inventory-unit">Unit</label>
      <input id="inventory-unit" required value={unit}
        onChange={(event) => setUnit(event.target.value)} />
      <label htmlFor="inventory-threshold">Positive reorder threshold</label>
      <input id="inventory-threshold" type="number" min="1" step="1" required
        value={threshold} onChange={(event) => setThreshold(event.target.value)} />
      <button type="submit" disabled={create.isPending}>Add item</button>
      <MutationMessage isPending={create.isPending} isError={create.isError}
        error={create.error} isSuccess={create.isSuccess} />
    </form>}
    {(adjust.isError) && <p role="alert">{adjust.error instanceof Error
      ? adjust.error.message : "The stock movement could not be recorded."}</p>}
  </ResourcePanel>;
}
