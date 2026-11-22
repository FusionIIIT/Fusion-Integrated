const express = require('express');
const PmsPatentService = require('../services/pms_patent_service');

const router = express.Router();
const pmsPatentService = new PmsPatentService();

function handleError(res, error) {
  const message = error && error.message ? error.message : 'Unexpected error';
  let status = 500;
  if (message.toLowerCase().includes('not found')) {
    status = 404;
  } else if (
    message.toLowerCase().includes('required')
    || message.toLowerCase().includes('invalid')
    || message.toLowerCase().includes('cannot')
    || message.toLowerCase().includes('must')
    || message.toLowerCase().includes('allowed')
    || message.toLowerCase().includes('deadline')
  ) {
    status = 400;
  }
  res.status(status).json({ error: message });
}

router.get('/pms/applications', async (req, res) => {
  try {
    const applications = await pmsPatentService.getApplications(req.query);
    res.status(200).json({ data: applications });
  } catch (error) {
    handleError(res, error);
  }
});

router.get('/pms/applications/:id', async (req, res) => {
  try {
    const application = await pmsPatentService.getApplication(Number(req.params.id));
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/draft', async (req, res) => {
  try {
    const application = await pmsPatentService.createDraft(req.body || {});
    res.status(201).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/submit', async (req, res) => {
  try {
    const application = await pmsPatentService.submitApplication(req.body || {});
    res.status(201).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/assign-director', async (req, res) => {
  try {
    const application = await pmsPatentService.assignDirector(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/review', async (req, res) => {
  try {
    const application = await pmsPatentService.reviewApplication(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/resubmit', async (req, res) => {
  try {
    const application = await pmsPatentService.resubmitApplication(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/assign-attorney', async (req, res) => {
  try {
    const application = await pmsPatentService.assignAttorney(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/attorney-response', async (req, res) => {
  try {
    const application = await pmsPatentService.respondAttorneyAssignment(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/budget-review', async (req, res) => {
  try {
    const application = await pmsPatentService.reviewBudget(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/file', async (req, res) => {
  try {
    const application = await pmsPatentService.recordFiling(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/grant', async (req, res) => {
  try {
    const application = await pmsPatentService.markGranted(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/applications/:id/withdraw', async (req, res) => {
  try {
    const application = await pmsPatentService.withdrawApplication(Number(req.params.id), req.body || {});
    res.status(200).json({ data: application });
  } catch (error) {
    handleError(res, error);
  }
});

router.get('/pms/admin/categories', async (req, res) => {
  try {
    const categories = await pmsPatentService.getCategories();
    res.status(200).json({ data: categories });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/pms/admin/categories', async (req, res) => {
  try {
    const category = await pmsPatentService.createCategory(req.body || {});
    res.status(201).json({ data: category });
  } catch (error) {
    handleError(res, error);
  }
});

router.put('/pms/admin/categories/:id', async (req, res) => {
  try {
    const category = await pmsPatentService.updateCategory(Number(req.params.id), req.body || {});
    res.status(200).json({ data: category });
  } catch (error) {
    handleError(res, error);
  }
});

module.exports = router;
