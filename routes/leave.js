const express = require('express');
const router = express.Router();
const leaveController = require('../controllers/leaveController');

router.get('/balance/:employeeId', leaveController.getLeaveBalance);

module.exports = router;
