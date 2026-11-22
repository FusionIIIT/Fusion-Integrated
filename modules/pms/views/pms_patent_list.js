function buildPatentListMarkup({ applications = [] } = {}) {
  const rows = applications.length
    ? applications.map((application) => `
      <tr>
        <td>${application.id || ''}</td>
        <td>${application.applicationCode || ''}</td>
        <td>${application.title || ''}</td>
        <td>${application.status || ''}</td>
        <td>${application.assignedDirectorId || '-'}</td>
        <td>${application.assignedAttorneyId || '-'}</td>
        <td>
          <button data-action="view" data-id="${application.id}">View</button>
          <button data-action="withdraw" data-id="${application.id}">Withdraw</button>
        </td>
      </tr>
    `).join('')
    : '<tr><td colspan="7">No patent applications found.</td></tr>';

  return `
    <div class="pms-patent-list">
      <h3>Patent Applications</h3>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Code</th>
            <th>Title</th>
            <th>Status</th>
            <th>Director</th>
            <th>Attorney</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

async function renderPatentList(context = {}) {
  let applications = context.applications || [];
  if (!applications.length && typeof fetch !== 'undefined') {
    const response = await fetch('/api/pms/applications');
    const result = await response.json();
    applications = result.data || [];
  }

  const markup = buildPatentListMarkup({ applications });
  if (typeof document !== 'undefined') {
    const container = document.createElement('div');
    container.innerHTML = markup;
    document.body.appendChild(container);

    container.querySelectorAll('[data-action]').forEach((button) => {
      button.addEventListener('click', async () => {
        const action = button.dataset.action;
        const id = Number(button.dataset.id || 0);

        if (action === 'withdraw') {
          const response = await fetch(`/api/pms/applications/${id}/withdraw`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: 'Withdrawn from list view.' }),
          });
          const result = await response.json();
          if (context.onAction) {
            context.onAction({ action, id, result });
          }
        } else if (context.onAction) {
          context.onAction({ action, id });
        }
      });
    });
  }

  return markup;
}

module.exports = {
  buildPatentListMarkup,
  renderPatentList,
};
