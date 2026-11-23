import { useState, type FormEvent } from "react";

import { useAuth } from "../../../auth/AuthProvider";
import { useFulfillRequisition, useInventory, useRequisitionDecision,
  useRequisitions, useSubmitRequisition } from "../api/hooks";
import { MutationMessage, ResourcePanel } from "../components/ResourcePanel";

export default function RequisitionsPage() {
  const { can } = useAuth();
  const requisitions = useRequisitions();
  const inventory = useInventory();
  const submit = useSubmitRequisition();
  const decide = useRequisitionDecision();
  const fulfill = useFulfillRequisition();
  const [itemId, setItemId] = useState("");
  const [quantity, setQuantity] = useState("1");

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submit.mutate({ lines: [{ item_id: Number(itemId), quantity: Number(quantity) }] });
  }

  return <ResourcePanel title="Inventory requisitions" data={requisitions.data}
    isPending={requisitions.isPending || (can("phc.requisition.create") && inventory.isPending)}
    isError={requisitions.isError || (can("phc.requisition.create") && inventory.isError)}
    error={requisitions.error ?? inventory.error} emptyText="No requisitions are available."
    renderRow={(requisition) => <article>
      <h2>Requisition {requisition.id}: {requisition.state.replaceAll("_", " ")}</h2>
      <ul>{requisition.lines.map((line) => <li key={line.item}>
        {line.quantity} {line.unit} — {line.item_name}
      </li>)}</ul>
      {requisition.state === "pending_approval" && can("phc.requisition.approve") && <>
        <button type="button" onClick={() => decide.mutate({ id: requisition.id, decision: "approve" })}>
          Approve requisition
        </button>
        <button type="button" onClick={() => decide.mutate({ id: requisition.id, decision: "reject" })}>
          Reject requisition
        </button>
      </>}
      {requisition.state === "approved" && can("phc.requisition.update") &&
        <button type="button" onClick={() => fulfill.mutate(requisition.id)}>Mark fulfilled</button>}
    </article>}>
    {can("phc.requisition.create") && <form onSubmit={create}>
      <h2>Submit an inventory requisition</h2>
      <label htmlFor="requisition-item">Item</label>
      <select id="requisition-item" required value={itemId}
        onChange={(event) => setItemId(event.target.value)}>
        <option value="">Choose an item</option>
        {(inventory.data?.results ?? []).filter((item) => item.is_active).map((item) => (
          <option key={item.id} value={item.id}>{item.name} ({item.unit})</option>
        ))}
      </select>
      <label htmlFor="requisition-quantity">Quantity</label>
      <input id="requisition-quantity" type="number" min="1" step="1" required
        value={quantity} onChange={(event) => setQuantity(event.target.value)} />
      <button type="submit" disabled={!itemId || submit.isPending}>Submit requisition</button>
      <MutationMessage isPending={submit.isPending} isError={submit.isError}
        error={submit.error} isSuccess={submit.isSuccess} />
    </form>}
    {[decide, fulfill].some((mutation) => mutation.isError) &&
      <p role="alert">The requisition could not be updated.</p>}
  </ResourcePanel>;
}
