const express = require('express');
const ElmLeaveService = require('../services/elm_leave_service');

const router = express.Router();
const elmLeaveService = new ElmLeaveService();

function handleError(res, error, fallbackStatus = 400) {
  const status = error && error.statusCode ? error.statusCode : fallbackStatus;
  res.status(status).json({
    success: false,
    message: error && error.message ? error.message : 'Unexpected error',
  });
}

router.get('/leave', async (req, res) => {
  try {
    const { employeeId, status, categoryId, fromDate, toDate } = req.query;
    const requests = await elmLeaveService.getLeaveRequests({
      employeeId: employeeId ? Number(employeeId) : undefined,
      status,
      categoryId: categoryId ? Number(categoryId) : undefined,
      fromDate,
      toDate,
    });
    res.status(200).json({ success: true, data: requests });
  } catch (error) {
    handleError(res, error);
  }
});

router.get('/leave/balances', async (req, res) => {
  try {
    const { employeeId } = req.query;
    const balances = await elmLeaveService.getEmployeeBalances(Number(employeeId));
    res.status(200).json({ success: true, data: balances });
  } catch (error) {
    handleError(res, error);
  }
});

router.get('/leave/:id', async (req, res) => {
  try {
    const leaveRequest = await elmLeaveService.getLeaveRequest(Number(req.params.id));
    const auditTrail = await elmLeaveService.getAuditTrail(Number(req.params.id));
    res.status(200).json({ success: true, data: { ...leaveRequest.toJSON(), auditTrail } });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/draft', async (req, res) => {
  try {
    const leaveRequest = await elmLeaveService.createDraft(req.body);
    res.status(201).json({ success: true, data: leaveRequest });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/submit', async (req, res) => {
  try {
    const leaveRequest = await elmLeaveService.submitLeave(req.body);
    res.status(201).json({ success: true, data: leaveRequest });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/:id/cancel', async (req, res) => {
  try {
    const request = await elmLeaveService.cancelLeaveRequest(Number(req.params.id), req.body || {});
    res.status(200).json({ success: true, data: request });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/:id/withdraw', async (req, res) => {
  try {
    const request = await elmLeaveService.withdrawLeaveRequest(Number(req.params.id), req.body || {});
    res.status(200).json({ success: true, data: request });
  } catch (error) {
    handleError(res, error);
  }
});

router.get('/leave/approvals/pending', async (req, res) => {
  try {
    const queue = await elmLeaveService.getPendingApprovals(req.query);
    res.status(200).json({ success: true, data: queue });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/approvals/:id/approve', async (req, res) => {
  try {
    const result = await elmLeaveService.approveRequest(Number(req.params.id), req.body || {});
    res.status(200).json({ success: true, data: result });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/approvals/:id/reject', async (req, res) => {
  try {
    const result = await elmLeaveService.rejectRequest(Number(req.params.id), req.body || {});
    res.status(200).json({ success: true, data: result });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/approvals/:id/forward', async (req, res) => {
  try {
    const result = await elmLeaveService.forwardRequest(Number(req.params.id), req.body || {});
    res.status(200).json({ success: true, data: result });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/approvals/:id/revoke', async (req, res) => {
  try {
    const result = await elmLeaveService.revokeApprovedLeave(Number(req.params.id), req.body || {});
    res.status(200).json({ success: true, data: result });
  } catch (error) {
    handleError(res, error);
  }
});

router.get('/leave/admin/categories', async (req, res) => {
  try {
    const categories = await elmLeaveService.getCategories();
    res.status(200).json({ success: true, data: categories });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/admin/categories', async (req, res) => {
  try {
    const category = await elmLeaveService.createCategory(req.body);
    res.status(201).json({ success: true, data: category });
  } catch (error) {
    handleError(res, error);
  }
});

router.put('/leave/admin/categories/:id', async (req, res) => {
  try {
    const category = await elmLeaveService.updateCategory(Number(req.params.id), req.body);
    res.status(200).json({ success: true, data: category });
  } catch (error) {
    handleError(res, error);
  }
});

router.post('/leave/admin/balances/adjust', async (req, res) => {
  try {
    const result = await elmLeaveService.adjustEmployeeBalance(req.body);
    res.status(200).json({ success: true, data: result });
  } catch (error) {
    handleError(res, error);
  }
});

router.get('/leave/admin/reports', async (req, res) => {
  try {
    const reports = await elmLeaveService.getLeaveReports(req.query);
    res.status(200).json({ success: true, data: reports });
  } catch (error) {
    handleError(res, error);
  }
});

module.exports = router;
