import React, { useState, useEffect } from "react";

// Minimal UI for Department Module (32b parameter style)
export default function DepartmentPage() {
  const [role, setRole] = useState("Faculty");
  const [username, setUsername] = useState("prof_smith");
  const [program, setProgram] = useState("BTech");
  const [batchYear, setBatchYear] = useState("2024");
  const [activeTab, setActiveTab] = useState("announcements");

  const [announcements, setAnnouncements] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [stockRequests, setStockRequests] = useState<any[]>([]);
  const [movementLogs, setMovementLogs] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [annTitle, setAnnTitle] = useState("");
  const [annContent, setAnnContent] = useState("");
  const [annTargetRole, setAnnTargetRole] = useState("ALL");
  const [annTargetProg, setAnnTargetProg] = useState("ALL");
  const [annTargetYear, setAnnTargetYear] = useState("");

  const [reqItemId, setReqItemId] = useState("");
  const [reqQty, setReqQty] = useState(1);
  const [reqPurpose, setReqPurpose] = useState("");

  const [invItemName, setInvItemName] = useState("");
  const [invQty, setInvQty] = useState(10);
  const [invUnit, setInvUnit] = useState("units");
  const [hodRemarks, setHodRemarks] = useState<{ [key: number]: string }>({});

  const headers = {
    "Content-Type": "application/json",
    "X-Username": username,
    "X-Role": role,
    "X-Program": program,
    "X-Batch-Year": batchYear,
  };

  const fetchAnnouncements = () => {
    fetch(`/api/v1/department/announcements/?role=${role}&program=${program}&batch_year=${batchYear}`, { headers })
      .then((res) => res.json()).then((data) => setAnnouncements(data.announcements || []))
      .catch((err) => console.error(err));
  };

  const fetchInventory = () => {
    fetch("/api/v1/department/inventory/", { headers })
      .then((res) => res.json()).then((data) => setInventory(data.items || []))
      .catch((err) => console.error(err));
  };

  const fetchStockRequests = () => {
    fetch("/api/v1/department/stock-requests/", { headers })
      .then((res) => res.json()).then((data) => setStockRequests(data.requests || []))
      .catch((err) => console.error(err));
  };

  const fetchMovementLogs = () => {
    fetch("/api/v1/department/movement-logs/", { headers })
      .then((res) => res.json()).then((data) => setMovementLogs(data.logs || []))
      .catch((err) => console.error(err));
  };

  useEffect(() => {
    fetchAnnouncements();
    fetchInventory();
    fetchStockRequests();
    fetchMovementLogs();
  }, [role, program, batchYear]);

  // UC-DEPT-002: Create Announcement
  const handleCreateAnnouncement = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(""); setError("");
    fetch("/api/v1/department/announcements/", {
      method: "POST", headers,
      body: JSON.stringify({
        title: annTitle, content: annContent, target_role: annTargetRole,
        target_program: annTargetProg, target_academic_year: annTargetYear ? parseInt(annTargetYear) : null,
      }),
    }).then(async (res) => {
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create announcement");
      setMessage("Announcement published successfully!");
      setAnnTitle(""); setAnnContent(""); fetchAnnouncements();
    }).catch((err) => setError(err.message));
  };

  // UC-DEPT-004: Request Stock Item
  const handleRequestStock = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(""); setError("");
    fetch("/api/v1/department/stock-requests/", {
      method: "POST", headers,
      body: JSON.stringify({ item_id: reqItemId, quantity: reqQty, purpose: reqPurpose }),
    }).then(async (res) => {
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to submit request");
      setMessage("Stock request submitted to HOD!");
      setReqPurpose(""); fetchStockRequests();
    }).catch((err) => setError(err.message));
  };

  // UC-DEPT-005: HOD Approve/Reject
  const handleDecision = (id: number, decision: "APPROVE" | "REJECT") => {
    setMessage(""); setError("");
    fetch(`/api/v1/department/stock-requests/${id}/decision/`, {
      method: "POST", headers,
      body: JSON.stringify({ decision, remarks: hodRemarks[id] || "" }),
    }).then(async (res) => {
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed decision");
      setMessage(`Request #${id} marked as ${decision === "APPROVE" ? "Approved" : "Rejected"}!`);
      fetchStockRequests();
    }).catch((err) => setError(err.message));
  };

  // UC-DEPT-006: Issue Stock
  const handleIssueStock = (id: number) => {
    setMessage(""); setError("");
    fetch(`/api/v1/department/stock-requests/${id}/issue/`, { method: "POST", headers })
      .then(async (res) => {
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed issuance");
        setMessage(`Stock for request #${id} issued successfully!`);
        fetchStockRequests(); fetchInventory(); fetchMovementLogs();
      }).catch((err) => setError(err.message));
  };

  const handleAddInventory = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(""); setError("");
    fetch("/api/v1/department/inventory/", {
      method: "POST", headers,
      body: JSON.stringify({ item_name: invItemName, quantity: invQty, unit: invUnit }),
    }).then(async (res) => {
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed adding inventory");
      setMessage("Inventory updated!");
      setInvItemName(""); fetchInventory(); fetchMovementLogs();
    }).catch((err) => setError(err.message));
  };

  return (
    <div style={{ padding: "12px", fontFamily: "sans-serif" }}>
      <h2>Department Module</h2>
      <div style={{ background: "#eee", padding: "8px", marginBottom: "12px", border: "1px solid #ccc" }}>
        <strong>Actor Switcher: </strong>
        <label> Role: </label>
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="Faculty">Faculty</option>
          <option value="HOD">HOD</option>
          <option value="Dept_Admin">Dept_Admin</option>
          <option value="Student">Student</option>
        </select>
        <label style={{ marginLeft: "10px" }}> Username: </label>
        <input style={{ width: "90px" }} value={username} onChange={(e) => setUsername(e.target.value)} />
        <label style={{ marginLeft: "10px" }}> Program: </label>
        <select value={program} onChange={(e) => setProgram(e.target.value)}>
          <option value="BTech">BTech</option>
          <option value="MTech">MTech</option>
          <option value="PhD">PhD</option>
        </select>
        <label style={{ marginLeft: "10px" }}> Year: </label>
        <input style={{ width: "50px" }} value={batchYear} onChange={(e) => setBatchYear(e.target.value)} />
      </div>

      {message && <div style={{ color: "green", marginBottom: "8px" }}>{message}</div>}
      {error && <div style={{ color: "red", marginBottom: "8px" }}>{error}</div>}

      <div style={{ display: "flex", gap: "6px", marginBottom: "12px" }}>
        <button onClick={() => setActiveTab("announcements")} style={{ fontWeight: activeTab === "announcements" ? "bold" : "normal" }}>Announcements</button>
        <button onClick={() => setActiveTab("request_stock")} style={{ fontWeight: activeTab === "request_stock" ? "bold" : "normal" }}>Request Stock (Faculty)</button>
        <button onClick={() => setActiveTab("hod_approval")} style={{ fontWeight: activeTab === "hod_approval" ? "bold" : "normal" }}>HOD Approvals</button>
        <button onClick={() => setActiveTab("issue_stock")} style={{ fontWeight: activeTab === "issue_stock" ? "bold" : "normal" }}>Stock Issuance & Inventory</button>
        <button onClick={() => setActiveTab("logs")} style={{ fontWeight: activeTab === "logs" ? "bold" : "normal" }}>Movement Logs</button>
      </div>

      {activeTab === "announcements" && (
        <div>
          <h3>Announcements (Targeted for {role})</h3>
          {["Faculty", "HOD", "Dept_Admin"].includes(role) && (
            <form onSubmit={handleCreateAnnouncement} style={{ border: "1px solid #ccc", padding: "8px", marginBottom: "10px" }}>
              <h4>Create Announcement (UC-DEPT-002)</h4>
              <input placeholder="Title" value={annTitle} onChange={(e) => setAnnTitle(e.target.value)} style={{ width: "240px", marginBottom: "4px" }} /><br />
              <textarea placeholder="Content" value={annContent} onChange={(e) => setAnnContent(e.target.value)} style={{ width: "240px", height: "40px", marginBottom: "4px" }} /><br />
              <label>Target Role: </label>
              <select value={annTargetRole} onChange={(e) => setAnnTargetRole(e.target.value)}>
                <option value="ALL">ALL</option>
                <option value="Student">Student</option>
                <option value="Faculty">Faculty</option>
              </select>
              <label style={{ marginLeft: "6px" }}>Program: </label>
              <input placeholder="ALL/BTech" value={annTargetProg} onChange={(e) => setAnnTargetProg(e.target.value)} style={{ width: "70px" }} />
              <label style={{ marginLeft: "6px" }}>Year: </label>
              <input placeholder="Year" value={annTargetYear} onChange={(e) => setAnnTargetYear(e.target.value)} style={{ width: "50px" }} />
              <button type="submit" style={{ display: "block", marginTop: "4px" }}>Publish</button>
            </form>
          )}
          <table border={1} cellPadding={4} style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#eee" }}>
                <th>ID</th><th>Title</th><th>Content</th><th>Author</th><th>Target</th><th>Date</th>
              </tr>
            </thead>
            <tbody>
              {announcements.map((a) => (
                <tr key={a.id}>
                  <td>{a.id}</td><td>{a.title}</td><td>{a.content}</td><td>{a.author_username} ({a.author_role})</td>
                  <td>{a.target_role}/{a.target_program}/{a.target_academic_year || "All"}</td><td>{a.created_at}</td>
                </tr>
              ))}
              {announcements.length === 0 && <tr><td colSpan={6}>No announcements for your scope.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "request_stock" && (
        <div>
          <h3>Faculty Stock Request (UC-DEPT-004)</h3>
          {role === "Faculty" ? (
            <form onSubmit={handleRequestStock} style={{ border: "1px solid #ccc", padding: "8px", marginBottom: "10px" }}>
              <h4>Submit Stock Request</h4>
              <label>Item: </label>
              <select value={reqItemId} onChange={(e) => setReqItemId(e.target.value)} required>
                <option value="">-- Choose Item --</option>
                {inventory.map((i) => (
                  <option key={i.id} value={i.id}>{i.item_name} (Avail: {i.available_quantity} {i.unit})</option>
                ))}
              </select>
              <label style={{ marginLeft: "8px" }}>Qty: </label>
              <input type="number" min="1" value={reqQty} onChange={(e) => setReqQty(parseInt(e.target.value))} style={{ width: "50px" }} required />
              <input placeholder="Purpose" value={reqPurpose} onChange={(e) => setReqPurpose(e.target.value)} style={{ width: "200px", marginLeft: "8px" }} />
              <button type="submit" style={{ marginLeft: "8px" }}>Submit</button>
            </form>
          ) : <p>Select Faculty role to submit request.</p>}
          <h4>Requests List</h4>
          <table border={1} cellPadding={4} style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#eee" }}>
                <th>ID</th><th>Item</th><th>Qty</th><th>Status</th><th>HOD Remarks</th><th>Date</th>
              </tr>
            </thead>
            <tbody>
              {stockRequests.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td><td>{r.item_name}</td><td>{r.quantity}</td>
                  <td>{r.status}</td><td>{r.hod_remarks}</td><td>{r.created_at}</td>
                </tr>
              ))}
              {stockRequests.length === 0 && <tr><td colSpan={6}>No requests.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "hod_approval" && (
        <div>
          <h3>HOD Approvals (UC-DEPT-005)</h3>
          <table border={1} cellPadding={4} style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#eee" }}>
                <th>ID</th><th>Requester</th><th>Item</th><th>Qty</th><th>Status</th><th>Remarks</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {stockRequests.filter((r) => r.status === "PENDING_HOD_APPROVAL").map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td><td>{r.requester_username}</td><td>{r.item_name}</td><td>{r.quantity}</td><td>{r.status}</td>
                  <td><input placeholder="Remarks" value={hodRemarks[r.id] || ""} onChange={(e) => setHodRemarks({ ...hodRemarks, [r.id]: e.target.value })} /></td>
                  <td>
                    <button onClick={() => handleDecision(r.id, "APPROVE")}>Approve</button>
                    <button onClick={() => handleDecision(r.id, "REJECT")} style={{ marginLeft: "4px" }}>Reject</button>
                  </td>
                </tr>
              ))}
              {stockRequests.filter((r) => r.status === "PENDING_HOD_APPROVAL").length === 0 && (
                <tr><td colSpan={7}>No pending requests.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "issue_stock" && (
        <div>
          <h3>Dept_Admin Stock Issuance (UC-DEPT-006) & Inventory</h3>
          <h4>Approved Requests Ready for Issue</h4>
          <table border={1} cellPadding={4} style={{ width: "100%", borderCollapse: "collapse", marginBottom: "12px" }}>
            <thead>
              <tr style={{ background: "#eee" }}>
                <th>ID</th><th>Requester</th><th>Item</th><th>Qty</th><th>Status</th><th>Action</th>
              </tr>
            </thead>
            <tbody>
              {stockRequests.filter((r) => r.status === "APPROVED_FOR_ISSUANCE").map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td><td>{r.requester_username}</td><td>{r.item_name}</td><td>{r.quantity}</td>
                  <td style={{ color: "green" }}>{r.status}</td>
                  <td><button onClick={() => handleIssueStock(r.id)}>Issue Stock</button></td>
                </tr>
              ))}
              {stockRequests.filter((r) => r.status === "APPROVED_FOR_ISSUANCE").length === 0 && (
                <tr><td colSpan={6}>No approved requests awaiting issue.</td></tr>
              )}
            </tbody>
          </table>
          <h4>Inventory Items</h4>
          {role === "Dept_Admin" && (
            <form onSubmit={handleAddInventory} style={{ border: "1px solid #ccc", padding: "8px", marginBottom: "8px" }}>
              <input placeholder="Item Name" value={invItemName} onChange={(e) => setInvItemName(e.target.value)} required />
              <input type="number" min="1" placeholder="Qty" value={invQty} onChange={(e) => setInvQty(parseInt(e.target.value))} style={{ width: "50px", marginLeft: "4px" }} required />
              <input placeholder="Unit" value={invUnit} onChange={(e) => setInvUnit(e.target.value)} style={{ width: "50px", marginLeft: "4px" }} />
              <button type="submit" style={{ marginLeft: "4px" }}>Add Stock</button>
            </form>
          )}
          <table border={1} cellPadding={4} style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr style={{ background: "#eee" }}><th>ID</th><th>Item Name</th><th>Qty</th><th>Unit</th></tr></thead>
            <tbody>
              {inventory.map((i) => (
                <tr key={i.id}><td>{i.id}</td><td>{i.item_name}</td><td>{i.available_quantity}</td><td>{i.unit}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === "logs" && (
        <div>
          <h3>Immutable Movement Logs (BR-DEPT-016)</h3>
          <table border={1} cellPadding={4} style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#eee" }}>
                <th>ID</th><th>Item</th><th>Type</th><th>Qty</th><th>By</th><th>Notes</th><th>Date</th>
              </tr>
            </thead>
            <tbody>
              {movementLogs.map((l) => (
                <tr key={l.id}>
                  <td>{l.id}</td><td>{l.item_name}</td><td>{l.movement_type}</td><td>{l.quantity}</td>
                  <td>{l.performed_by}</td><td>{l.notes}</td><td>{l.created_at}</td>
                </tr>
              ))}
              {movementLogs.length === 0 && <tr><td colSpan={7}>No movement logs found.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
