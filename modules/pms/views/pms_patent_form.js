function buildPatentFormMarkup({ applicantId = 1, categories = [] } = {}) {
  const options = categories.length
    ? categories.map((category) => `<option value="${category.id}">${category.name}</option>`).join('')
    : '<option value="">Select category</option>';

  return `
    <div class="pms-patent-form">
      <h3>Patent Application Form</h3>
      <form id="pmsPatentForm">
        <input type="hidden" name="applicantId" value="${applicantId}" />
        <div class="field">
          <label>Category</label>
          <select name="categoryId">${options}</select>
        </div>
        <div class="field">
          <label>Title</label>
          <input type="text" name="title" />
        </div>
        <div class="field">
          <label>Abstract</label>
          <textarea name="abstract" rows="3"></textarea>
        </div>
        <div class="field">
          <label>Detailed Description</label>
          <textarea name="detailedDescription" rows="4"></textarea>
        </div>
        <div class="field">
          <label>Claims</label>
          <textarea name="claims" rows="4"></textarea>
        </div>
        <div class="field">
          <label>Supporting PDF URL</label>
          <input type="url" name="supportingDocumentUrl" placeholder="https://..." />
        </div>
        <div class="actions">
          <button type="button" data-action="draft">Save Draft</button>
          <button type="button" data-action="submit">Submit Application</button>
        </div>
      </form>
    </div>
  `;
}

function renderPatentForm(context = {}) {
  const markup = buildPatentFormMarkup(context);
  if (typeof document !== 'undefined') {
    const container = document.createElement('div');
    container.innerHTML = markup;
    document.body.appendChild(container);

    container.querySelectorAll('[data-action]').forEach((button) => {
      button.addEventListener('click', async () => {
        const form = button.closest('form');
        const payload = Object.fromEntries(new FormData(form));
        payload.applicantId = Number(payload.applicantId || context.applicantId || 1);
        payload.categoryId = payload.categoryId ? Number(payload.categoryId) : null;
        payload.supportingDocumentMimeType = 'application/pdf';

        const action = button.dataset.action;
        const endpoint = action === 'draft'
          ? '/api/pms/applications/draft'
          : '/api/pms/applications/submit';
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
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
  buildPatentFormMarkup,
  renderPatentForm,
};
