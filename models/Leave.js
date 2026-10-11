const db = require('../db');

class Leave {
  static async getLeaveBalanceByEmployeeId(employeeId) {
    const query = `
      SELECT 
        CL, RH, SCL, EL, COL, VL
      FROM 
        leave_balances
      WHERE 
        employee_id = $1;
    `;
    const values = [employeeId];
    const result = await db.query(query, values);
    return result.rows[0] || { CL: 0, RH: 0, SCL: 0, EL: 0, COL: 0, VL: 0 };
  }
}

module.exports = Leave;
