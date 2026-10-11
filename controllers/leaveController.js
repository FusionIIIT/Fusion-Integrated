const Leave = require('../models/Leave');

exports.getLeaveBalance = async (req, res) => {
  const { employeeId } = req.params;

  try {
    const leaveBalance = await Leave.getLeaveBalanceByEmployeeId(employeeId);
    res.status(200).json(leaveBalance);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch leave balance' });
  }
};
