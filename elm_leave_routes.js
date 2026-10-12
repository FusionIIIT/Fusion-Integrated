// path/to/modules/elm/routes/elm_leave_routes.js
import express from 'express';
import elmLeaveController from './elm_leave_controller';
import { useElmLeaveService } from '../services';

const router = express.Router();
const elmLeaveService = new ElmLeaveService();

router.get('/leave', async (req, res) => {
  const { employeeId } = req.query;
  try {
    const leaveRequests = await elmLeaveService.getLeaveRequests(employeeId);
    res.status(200).json(leaveRequests);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

router.get('/leave/:id', async (req, res) => {
  const { id } = req.params;
  try {
    const leaveRequest = await elmLeaveService.getLeaveRequest(id);
    res.status(200).json(leaveRequest);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

router.post('/leave', async (req, res) => {
  const { employeeId, categoryId, startDate, endDate } = req.body;
  try {
    const leaveRequest = await elmLeaveService.applyForLeave(employeeId, categoryId, startDate, endDate);
    res.status(201).json(leaveRequest);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

router.put('/leave/:id', async (req, res) => {
  const { id, categoryId, startDate, endDate } = req.body;
  try {
    const leaveRequest = await elmLeaveService.updateLeaveRequest(id, categoryId, startDate, endDate);
    res.status(200).json(leaveRequest);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

router.delete('/leave/:id', async (req, res) => {
  const { id } = req.params;
  try {
    await elmLeaveService.cancelLeave(id);
    res.status(204).send();
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});

export default router;
