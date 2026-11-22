function buildLeaveDetailMarkup({ leave = {}, auditTrail = [] } = {}) {
  const trail = auditTrail.length
    ? auditTrail.map((entry) => `<li><strong>${entry.action || 'Update'}</strong> — ${entry.actor || 'System'}: ${entry.detail || ''}</li>`).join('')
    : '<li>No workflow history available.</li>';

  return `
    <div class="elm-leave-detail">
      <h3>Leave Request #${leave.id || ''}</h3>
      <dl>
        <dt>Status</dt><dd>${leave.status || ''}</dd>
        <dt>Category</dt><dd>${leave.categoryId || ''}</dd>
        <dt>Period</dt><dd>${leave.startDate || ''} to ${leave.endDate || ''}</dd>
        <dt>Days</dt><dd>${leave.chargeableDays || 0}</dd>
        <dt>Reason</dt><dd>${leave.reason || leave.purpose || ''}</dd>
      </dl>
      <h4>Workflow Timeline</h4>
      <ul>${trail}</ul>
      <div class="actions">
        <button data-action="approve">Approve</button>
        <button data-action="reject">Reject</button>
        <button data-action="forward">Forward</button>
        <button data-action="cancel">Cancel</button>
        <button data-action="revoke">Revoke</button>
      </div>
    </div>
  `;
}

async function renderLeaveDetail(context = {}) {
  const markup = buildLeaveDetailMarkup(context);
  if (typeof document !== 'undefined') {
    const root = document.createElement('div');
    root.innerHTML = markup;
    document.body.appendChild(root);
    root.querySelectorAll('[data-action]').forEach((button) => {
      button.addEventListener('click', async () => {
        const action = button.dataset.action;
        const id = context.leave && context.leave.id ? context.leave.id : 0;
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
  buildLeaveDetailMarkup,
  renderLeaveDetail,
};
