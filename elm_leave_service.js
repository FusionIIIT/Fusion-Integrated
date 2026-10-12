// path/to/modules/elm/services/elm_leave_service.js
import { Op } from 'sequelize';
import { ElmLeaveCategory, ElmLeaveBalance, ElmLeaveRequest } from '../models';

class ElmLeaveService {
  async applyForLeave(employeeId, categoryId, startDate, endDate) {
    const leaveCategory = await ElmLeaveCategory.findByPk(categoryId);
    if (!leaveCategory) {
      throw new Error('Invalid leave category');
    }

    const balance = await ElmLeaveBalance.findOne({
      where: {
        employeeId,
        categoryId,
      },
    });

    if (!balance) {
      throw new Error('Insufficient leave balance');
    }

    if (balance.balance < 1) {
      throw new Error('Insufficient leave balance');
    }

    const leaveRequest = await ElmLeaveRequest.create({
      employeeId,
      categoryId,
      startDate,
      endDate,
      status: 'draft',
    });

    balance.balance -= 1;
    await balance.save();

    return leaveRequest;
  }

  async respondToSubstitute(substituteId, leaveRequestId) {
    const leaveRequest = await ElmLeaveRequest.findByPk(leaveRequestId);
    if (!leaveRequest) {
      throw new Error('Invalid leave request');
    }

    if (leaveRequest.status !== 'awaiting_substitute_response') {
      throw new Error('Invalid leave request status');
    }

    const substitute = await User.findByPk(substituteId);
    if (!substitute) {
      throw new Error('Invalid substitute');
    }

    leaveRequest.substituteId = substituteId;
    leaveRequest.status = 'awaiting_unit_head_review';
    await leaveRequest.save();

    return leaveRequest;
  }

  async approveLeave(leaveRequestId) {
    const leaveRequest = await ElmLeaveRequest.findByPk(leaveRequestId);
    if (!leaveRequest) {
      throw new Error('Invalid leave request');
    }

    if (leaveRequest.status !== 'awaiting_unit_head_review') {
      throw new Error('Invalid leave request status');
    }

    leaveRequest.status = 'awaiting_establishment_routing';
    await leaveRequest.save();

    return leaveRequest;
  }

  async cancelLeave(leaveRequestId) {
    const leaveRequest = await ElmLeaveRequest.findByPk(leaveRequestId);
    if (!leaveRequest) {
      throw new Error('Invalid leave request');
    }

    if (leaveRequest.status !== 'submitted') {
      throw new Error('Invalid leave request status');
    }

    leaveRequest.status = 'cancelled';
    await leaveRequest.save();

    return leaveRequest;
  }

  async extendLeave(leaveRequestId, additionalDays) {
    const leaveRequest = await ElmLeaveRequest.findByPk(leaveRequestId);
    if (!leaveRequest) {
      throw new Error('Invalid leave request');
    }

    if (leaveRequest.status !== 'ongoing') {
      throw new Error('Invalid leave request status');
    }

    leaveRequest.endDate = leaveRequest.endDate.addDays(additionalDays);
    await leaveRequest.save();

    return leaveRequest;
  }

  async resumeLeave(leaveRequestId, actualReturnDate) {
    const leaveRequest = await ElmLeaveRequest.findByPk(leaveRequestId);
    if (!leaveRequest) {
      throw new Error('Invalid leave request');
    }

    if (leaveRequest.status !== 'ongoing') {
      throw new Error('Invalid leave request status');
    }

    leaveRequest.endDate = actualReturnDate;
    await leaveRequest.save();

    return leaveRequest;
  }

  async withdrawLeave(leaveRequestId) {
    const leaveRequest = await ElmLeaveRequest.findByPk(leaveRequestId);
    if (!leaveRequest) {
      throw new Error('Invalid leave request');
    }

    if (leaveRequest.status !== 'draft') {
      throw new Error('Invalid leave request status');
    }

    leaveRequest.status = 'withdrawn';
    await leaveRequest.save();

    return leaveRequest;
  }

  async getLeaveRequests(employeeId) {
    const leaveRequests = await ElmLeaveRequest.findAll({
      where: {
        employeeId,
      },
    });

    return leaveRequests;
  }

  async getLeaveRequest(id) {
    const leaveRequest = await ElmLeaveRequest.findByPk(id);
    if (!leaveRequest) {
      throw new Error('Invalid leave request');
    }

    return leaveRequest;
  }

  async updateLeaveRequest(id, categoryId, startDate, endDate) {
    const leaveRequest = await ElmLeaveRequest.findByPk(id);
    if (!leaveRequest) {
      throw new Error('Invalid leave request');
    }

    leaveRequest.categoryId = categoryId;
    leaveRequest.startDate = startDate;
    leaveRequest.endDate = endDate;
    await leaveRequest.save();

    return leaveRequest;
  }
}

export default ElmLeaveService;
