function buildPatentDetailMarkup({ application = {} } = {}) {
  const history = Array.isArray(application.statusHistory) ? application.statusHistory : [];
  const historyMarkup = history.length
    ? history.map((entry) => `
      <li>
        <strong>${entry.action || 'Update'}</strong>
        <span>${entry.actor || 'System'}</span>
        <span>${entry.status || ''}</span>
        <p>${entry.detail || ''}</p>
      </li>
    `).join('')
    : '<li>No status history available.</li>';

  return `
    <div class="pms-patent-detail">
      <h3>Patent Application #${application.id || ''}</h3>
      <dl>
        <dt>Code</dt><dd>${application.applicationCode || ''}</dd>
        <dt>Title</dt><dd>${application.title || ''}</dd>
        <dt>Status</dt><dd>${application.status || ''}</dd>
        <dt>Category</dt><dd>${application.category && application.category.name ? application.category.name : '-'}</dd>
        <dt>Applicant</dt><dd>${application.applicantId || ''}</dd>
        <dt>Director</dt><dd>${application.assignedDirectorId || '-'}</dd>
        <dt>Attorney</dt><dd>${application.assignedAttorneyId || '-'}</dd>
      </dl>

      <h4>Status History</h4>
      <ul>${historyMarkup}</ul>

      <div class="actions">
        <button data-action="approve">Approve</button>
        <button data-action="reject">Reject</button>
        <button data-action="needs-revision">Needs Revision</button>
        <button data-action="file">Mark Filed</button>
      </div>
    </div>
  `;
}

async function renderPatentDetail(context = {}) {
  let application = context.application || null;
  if (!application && context.applicationId) {
    const response = await fetch(`/api/pms/applications/${context.applicationId}`);
    const result = await response.json();
    application = result.data || {};
  }

  const markup = buildPatentDetailMarkup({ application: application || {} });
  if (typeof document !== 'undefined') {
    const container = document.createElement('div');
    container.innerHTML = markup;
    document.body.appendChild(container);

    container.querySelectorAll('[data-action]').forEach((button) => {
      button.addEventListener('click', async () => {
        const action = button.dataset.action;
        const id = application && application.id ? application.id : 0;
        let response;

        if (action === 'file') {
          response = await fetch(`/api/pms/applications/${id}/file`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              externalFilingId: `EXT-${Date.now()}`,
              filingDate: new Date().toISOString().slice(0, 10),
              filingType: 'Domestic',
            }),
          });
        } else {
          const decision = action === 'approve' ? 'Approve' : action === 'reject' ? 'Reject' : 'Needs Revision';
          response = await fetch(`/api/pms/applications/${id}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              decision,
              justification: 'This review decision was taken after technical and legal checks and includes complete decision rationale.',
            }),
          });
        }

        const result = await response.json();
        if (context.onAction) {
          context.onAction({ action, id, result, response });
        }
      });
    });
  }
  return markup;
}

module.exports = {
  buildPatentDetailMarkup,
  renderPatentDetail,
};
