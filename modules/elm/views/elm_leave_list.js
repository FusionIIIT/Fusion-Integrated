function buildLeaveListMarkup({ leaves = [], pending = [], employeeId = 1 } = {}) {
  const rows = leaves.length
    ? leaves.map((leave) => `
      <tr>
        <td>${leave.id || ''}</td>
        <td>${leave.categoryId || ''}</td>
        <td>${leave.startDate || ''}</td>
        <td>${leave.endDate || ''}</td>
        <td>${leave.status || ''}</td>
        <td>${leave.chargeableDays || 0}</td>
      </tr>
    `).join('')
    : '<tr><td colspan="6">No leave records</td></tr>';

  const queue = pending.length
    ? pending.map((leave) => `
      <li>
        <span>Request #${leave.id}</span>
        <span>${leave.status}</span>
        <button data-request-id="${leave.id}" data-action="approve">Approve</button>
        <button data-request-id="${leave.id}" data-action="reject">Reject</button>
      </li>
    `).join('')
    : '<li>No pending approvals</li>';

  return `
    <div class="elm-leave-list">
      <h3>Leave Summary</h3>
      <div class="summary-cards">
        <div class="card"><strong>Employee</strong><span>${employeeId}</span></div>
        <div class="card"><strong>Requests</strong><span>${leaves.length}</span></div>
        <div class="card"><strong>Pending</strong><span>${pending.length}</span></div>
      </div>
      <h4>Leave History</h4>
      <table>
        <thead>
          <tr><th>ID</th><th>Category</th><th>From</th><th>To</th><th>Status</th><th>Days</th></tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      <h4>Approver Pending Queue</h4>
      <ul>${queue}</ul>
    </div>
  `;
}

async function renderLeaveList(context = {}) {
  const markup = buildLeaveListMarkup(context);
  if (typeof document !== 'undefined') {
    const root = document.createElement('div');
    root.innerHTML = markup;
    document.body.appendChild(root);
    root.querySelectorAll('[data-action]').forEach((button) => {
      button.addEventListener('click', async () => {
        const action = button.dataset.action;
        const id = button.dataset.requestId;
        const response = await fetch(`/api/leave/approvals/${id}/${action}`, { method: 'POST' });
        const result = await response.json();
        if (context.onAction) {
          context.onAction({ action, id, result });
        }
      });
    });
  }
  return markup;
}

module.exports = {
  buildLeaveListMarkup,
  renderLeaveList,
};
