import { useEffect, useState, type FormEvent } from "react";
import { iaaApi } from "../api/client";

export default function ConfigurationPage() {
  const [policy, setPolicy] = useState({ name: "IAA Global Policy", financial_year_start_month: 4, ta_high_value_threshold: "", approval_timeout_hours: "", parameters: {} as object });
  const [routes, setRoutes] = useState<Array<{ id: number; request_type: string; department: string; amount_from: string; amount_through: string | null; level: number; authority_role: string; assignee_user_id: number | null; timeout_hours: number | null; next_route: number | null; is_active: boolean }>>([]);
  const [budgets, setBudgets] = useState<Array<{ id: number; department: string; financial_year: string; budget_code: string; allocated_amount: string; committed_amount: string; available_amount: string }>>([]);
  const [routeForm, setRouteForm] = useState({ request_type: "expense", department: "", amount_from: "0", amount_through: "", level: "1", authority_role: "hod", assignee_user_id: "", timeout_hours: "", next_route: "" });
  const [budgetForm, setBudgetForm] = useState({ department: "", financial_year: "", budget_code: "", allocated_amount: "", committed_amount: "0", available_amount: "" });
  const [error, setError] = useState(""); const [message, setMessage] = useState("");
  const refresh = () => Promise.all([iaaApi.policy(), iaaApi.approvalRoutes(), iaaApi.budgets()]).then(([p, r, b]) => {
    if (p) setPolicy({ name: p.name, financial_year_start_month: p.financial_year_start_month,
      ta_high_value_threshold: p.ta_high_value_threshold ?? "", approval_timeout_hours: p.approval_timeout_hours?.toString() ?? "", parameters: p.parameters });
    setRoutes(r);
    setBudgets(b);
  }).catch((e) => setError(e.message));
  useEffect(() => { void refresh(); }, []);
  async function save(event: FormEvent) {
    event.preventDefault(); setError(""); setMessage("");
    try { await iaaApi.updatePolicy({ ...policy,
      ta_high_value_threshold: policy.ta_high_value_threshold || null,
      approval_timeout_hours: policy.approval_timeout_hours ? Number(policy.approval_timeout_hours) : null,
      is_active: true }); setMessage("Policy saved."); }
    catch (e) { setError((e as Error).message); }
  }
  async function addRoute(event: FormEvent) {
    event.preventDefault(); setError("");
    try { await iaaApi.addApprovalRoute({ ...routeForm,
      amount_from: routeForm.amount_from, amount_through: routeForm.amount_through || null,
      level: Number(routeForm.level), assignee_user_id: Number(routeForm.assignee_user_id),
      timeout_hours: routeForm.timeout_hours ? Number(routeForm.timeout_hours) : null,
      next_route: routeForm.next_route ? Number(routeForm.next_route) : null, is_active: true });
      await refresh(); setMessage("Approval route added."); }
    catch (e) { setError((e as Error).message); }
  }
  async function addBudget(event: FormEvent) {
    event.preventDefault(); setError("");
    try { await iaaApi.addBudget({ ...budgetForm, allocated_amount: budgetForm.allocated_amount,
      committed_amount: budgetForm.committed_amount, available_amount: budgetForm.available_amount });
      await refresh(); setMessage("Budget allocation saved."); }
    catch (e) { setError((e as Error).message); }
  }
  return <main className="iaa-page"><header><h1>IAA configuration</h1><p>Configure policy values and role-specific approval routes.</p></header>
    {error && <p className="iaa-error" role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    <form className="iaa-card iaa-form" onSubmit={save}><h2>Policy</h2>
      <label>Financial year start month<input type="number" min="1" max="12" value={policy.financial_year_start_month} onChange={(e) => setPolicy({ ...policy, financial_year_start_month: Number(e.target.value) })} /></label>
      <label>High-value TA threshold<input type="number" min="0" step="0.01" value={policy.ta_high_value_threshold} onChange={(e) => setPolicy({ ...policy, ta_high_value_threshold: e.target.value })} /></label>
      <label>Approval timeout (hours)<input type="number" min="1" value={policy.approval_timeout_hours} onChange={(e) => setPolicy({ ...policy, approval_timeout_hours: e.target.value })} /></label>
      <button>Save policy</button>
    </form>
    <section className="iaa-card"><h2>Approval routes</h2><div className="iaa-table-wrap"><table><thead><tr><th>Type</th><th>Department</th><th>Amount band</th><th>Level</th><th>Authority</th><th>Assignee</th></tr></thead>
      <tbody>{routes.map((route) => <tr key={route.id}><td>{route.request_type}</td><td>{route.department || "Any"}</td><td>{route.amount_from} – {route.amount_through ?? "No upper limit"}</td><td>{route.level}</td><td>{route.authority_role}</td><td>{route.assignee_user_id ?? "Unassigned"}</td></tr>)}</tbody>
    </table></div><form className="iaa-form" onSubmit={addRoute}><h3>Add an approval level</h3>
      <label>Request type<input value={routeForm.request_type} onChange={(e) => setRouteForm({ ...routeForm, request_type: e.target.value })} required /></label>
      <label>Department or blank for any<input value={routeForm.department} onChange={(e) => setRouteForm({ ...routeForm, department: e.target.value })} /></label>
      <label>Amount from<input type="number" min="0" step="0.01" value={routeForm.amount_from} onChange={(e) => setRouteForm({ ...routeForm, amount_from: e.target.value })} /></label>
      <label>Amount through<input type="number" min="0" step="0.01" value={routeForm.amount_through} onChange={(e) => setRouteForm({ ...routeForm, amount_through: e.target.value })} /></label>
      <label>Level<input type="number" min="1" value={routeForm.level} onChange={(e) => setRouteForm({ ...routeForm, level: e.target.value })} /></label>
      <label>Authority<select value={routeForm.authority_role} onChange={(e) => setRouteForm({ ...routeForm, authority_role: e.target.value })}><option value="hod">HoD</option><option value="dean">Dean</option><option value="director">Director</option></select></label>
      <label>Assigned user ID<input type="number" min="1" value={routeForm.assignee_user_id} onChange={(e) => setRouteForm({ ...routeForm, assignee_user_id: e.target.value })} required /></label>
      <label>Timeout hours (optional)<input type="number" min="1" value={routeForm.timeout_hours} onChange={(e) => setRouteForm({ ...routeForm, timeout_hours: e.target.value })} /></label>
      <label>Next route ID (optional)<input type="number" min="1" value={routeForm.next_route} onChange={(e) => setRouteForm({ ...routeForm, next_route: e.target.value })} /></label>
      <button>Add route level</button>
    </form></section>
    <section className="iaa-card"><h2>Financial-year budgets</h2><div className="iaa-table-wrap"><table><thead><tr><th>Year</th><th>Department</th><th>Code</th><th>Allocated</th><th>Committed</th><th>Available</th></tr></thead><tbody>
      {budgets.map((budget) => <tr key={budget.id}><td>{budget.financial_year}</td><td>{budget.department}</td><td>{budget.budget_code}</td><td>{budget.allocated_amount}</td><td>{budget.committed_amount}</td><td>{budget.available_amount}</td></tr>)}
    </tbody></table></div><form className="iaa-form" onSubmit={addBudget}><h3>Add a budget allocation</h3>
      <label>Financial year (YYYY-YYYY)<input value={budgetForm.financial_year} onChange={(e) => setBudgetForm({ ...budgetForm, financial_year: e.target.value })} required /></label>
      <label>Department<input value={budgetForm.department} onChange={(e) => setBudgetForm({ ...budgetForm, department: e.target.value })} required /></label>
      <label>Budget code<input value={budgetForm.budget_code} onChange={(e) => setBudgetForm({ ...budgetForm, budget_code: e.target.value })} required /></label>
      <label>Allocated amount<input type="number" min="0" step="0.01" value={budgetForm.allocated_amount} onChange={(e) => setBudgetForm({ ...budgetForm, allocated_amount: e.target.value })} required /></label>
      <label>Committed amount<input type="number" min="0" step="0.01" value={budgetForm.committed_amount} onChange={(e) => setBudgetForm({ ...budgetForm, committed_amount: e.target.value })} required /></label>
      <label>Available amount<input type="number" min="0" step="0.01" value={budgetForm.available_amount} onChange={(e) => setBudgetForm({ ...budgetForm, available_amount: e.target.value })} required /></label>
      <button>Add budget</button>
    </form></section>
  </main>;
}
