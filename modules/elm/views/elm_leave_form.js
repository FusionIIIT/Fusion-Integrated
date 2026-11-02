function buildLeaveFormMarkup({ employeeId = 1, balances = [], onSubmit } = {}) {
  const options = balances.length
    ? balances.map((balance) => `<option value="${balance.categoryId || ''}">${balance.categoryId || 'Category'}</option>`).join('')
    : '<option value="">Select category</option>';

  return `
    <div class="elm-leave-form">
      <h3>Employee Leave Application</h3>
      <form id="elmLeaveForm">
        <input type="hidden" name="employeeId" value="${employeeId}" />
        <div class="field">
          <label>Leave Category</label>
          <select name="categoryId">${options}</select>
        </div>
        <div class="field">
          <label>Start Date</label>
          <input type="date" name="startDate" />
        </div>
        <div class="field">
          <label>End Date</label>
          <input type="date" name="endDate" />
        </div>
        <div class="field">
          <label>Half Day</label>
          <input type="checkbox" name="halfDay" />
        </div>
        <div class="field">
          <label>Reason</label>
          <textarea name="reason" rows="3"></textarea>
        </div>
        <div class="field">
          <label>Supporting Document URL</label>
          <input type="url" name="attachmentUrl" placeholder="https://..." />
        </div>
        <div class="actions">
          <button type="button" class="secondary" data-action="draft">Save Draft</button>
          <button type="button" data-action="submit">Submit</button>
        </div>
      </form>
    </div>
  `;
}

function renderLeaveForm(context = {}) {
  const markup = buildLeaveFormMarkup(context);
  if (typeof document !== 'undefined') {
    const container = document.createElement('div');
    container.innerHTML = markup;
    document.body.appendChild(container);
    container.querySelectorAll('[data-action]').forEach((button) => {
      button.addEventListener('click', async () => {
        const form = button.closest('form');
        const payload = Object.fromEntries(new FormData(form));
        const action = button.dataset.action;
        const response = await fetch(`/api/leave/${action === 'draft' ? 'draft' : 'submit'}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...payload,
            employeeId: Number(payload.employeeId || context.employeeId || 1),
            categoryId: Number(payload.categoryId || 0),
            halfDay: Boolean(payload.halfDay),
          }),
        });
        const result = await response.json();
        if (context.onSubmit) {
          context.onSubmit({ action, result, response });
        }
      });
    });
  }
  return markup;
}

module.exports = {
  buildLeaveFormMarkup,
  renderLeaveForm,
};
