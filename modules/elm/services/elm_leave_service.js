const { Op } = require('sequelize');
const ElmLeaveCategory = require('../models/elm_leave_categories');
const ElmLeaveBalance = require('../models/elm_leave_balances');
const ElmLeaveRequest = require('../models/elm_leave_requests');

class ElmLeaveService {
 static normalizeNumeric(value) {
   const number = Number(value || 0);
   return Number.isFinite(number) ? Number(number.toFixed(2)) : 0;
 }

 static toDate(dateValue) {
   const date = new Date(dateValue);
   if (Number.isNaN(date.getTime())) {
     throw new Error('Date value is invalid.');
   }
   return date;
 }

 static addDays(dateValue, amount) {
   const date = new Date(dateValue);
   date.setDate(date.getDate() + amount);
   return date;
 }

 static getDateString(dateValue) {
   const date = new Date(dateValue);
   return date.toISOString().slice(0, 10);
 }

 static async validateCategory(categoryId, categoryName) {
   const category = categoryId ? await ElmLeaveCategory.findByPk(categoryId) : categoryName ? await ElmLeaveCategory.findOne({ where: { name: categoryName } }) : null;
   if (!category) {
     throw new Error('Invalid leave category.');
   }
   return category;
 }

 static async ensureBalanceForEmployee(employeeId, categoryId) {
   const balance = await ElmLeaveBalance.findOne({ where: { employeeId, categoryId } });
   if (balance) {
     return balance;
   }

   return ElmLeaveBalance.create({
     employeeId,
     categoryId,
     balance: 0,
     accruedDays: 0,
     usedDays: 0,
   });
 }

 static getReqStatusTransitionAllowed(currentStatus, nextStatus) {
   const allowed = {
     Draft: ['Submitted', 'Cancelled'],
     Submitted: ['Pending Approval', 'Cancelled', 'Rejected'],
     'Pending Approval': ['Approved', 'Rejected', 'Forwarded'],
     Forwarded: ['Approved', 'Rejected', 'Pending Approval'],
     Approved: ['Cancelled', 'Revoked'],
     Rejected: [],
     Cancelled: [],
     Revoked: [],
   };
   return (allowed[currentStatus] || []).includes(nextStatus);
 }

 static countWorkingDays(startDate, endDate, categoryName, halfDay = false) {
   if (!(startDate && endDate)) {
     return 0;
    }

   const start = new Date(startDate);
   const end = new Date(endDate);
   const totalDays = Math.floor((end - start) / 86400000) + 1;
   if (halfDay) {
     return 0.5;
   }

   const continuousCategories = ['EL', 'COL', 'VL'];
   if (continuousCategories.includes(categoryName)) {
     return totalDays;
    }

   let count = 0;
   for (let i = 0; i < totalDays; i += 1) {
     const current = new Date(start);
     current.setDate(start.getDate() + i);
     const day = current.getDay();
     if (day !== 0 && day !== 6) {
       count += 1;
     }
   }
   return count;
 }

 async ensureLeaveEligibility({ employeeId, categoryId, startDate, endDate, categoryName, halfDay = false }) {
   const category = await ElmLeaveService.validateCategory(categoryId, categoryName);
   const chargeableDays = ElmLeaveService.countWorkingDays(startDate, endDate, category.name, halfDay);

   if (!employeeId || !Number.isFinite(Number(employeeId))) {
     throw new Error('Employee identifier is required.');
    }
   if (Number(endDate) < Number(startDate)) {
     throw new Error('End date cannot be earlier than start date.');
   }
   if (chargeableDays <= 0) {
     throw new Error('Requested leave duration must be greater than zero.');
   }

   const balance = await ElmLeaveService.ensureBalanceForEmployee(Number(employeeId), category.id);
   if (Number(balance.balance) < chargeableDays) {
     throw new Error(`Insufficient balance for ${category.name}. Available: ${Number(balance.balance).toFixed(2)}`);
   }

   return { category, balance, chargeableDays };
 }

 async createDraft(payload = {}) {
   const { employeeId, categoryId, categoryName, startDate, endDate, reason, purpose, halfDay = false, halfDayType = 'None', isStationLeave = false, stationLeaveDetails = '', attachmentUrl } = payload;
   const category = await ElmLeaveService.validateCategory(categoryId, categoryName || null);
   const chargeableDays = ElmLeaveService.countWorkingDays(startDate, endDate, category.name, halfDay);

   if (!employeeId) {
     throw new Error('Employee id is required.');
   }
   if (!startDate || !endDate) {
     throw new Error('Start date and end date are required.');
   }
   if (new Date(endDate) < new Date(startDate)) {
     throw new Error('End date cannot be earlier than start date.');
   }
   if (chargeableDays <= 0) {
     throw new Error('Requested leave duration must be greater than zero.');
    }

   const overlap = await ElmLeaveRequest.findAll({
     where: {
       employeeId: Number(employeeId),
       status: { [Op.in]: ['Submitted', 'Pending Approval', 'Forwarded', 'Approved'] },
     },
   });

   for (const record of overlap) {
     const existingStart = new Date(record.startDate);
     const existingEnd = new Date(record.endDate);
     const requestedStart = new Date(startDate);
     const requestedEnd = new Date(endDate);
     const hasOverlap = requestedStart <= existingEnd && requestedEnd >= existingStart;
     if (hasOverlap) {
       throw new Error('Leave request overlaps with an active or approved leave period.');
     }
   }

   const request = await ElmLeaveRequest.create({
     employeeId: Number(employeeId),
     categoryId: category.id,
     startDate,
     endDate,
     status: 'Draft',
     purpose: purpose || reason || '',
     reason: reason || purpose || '',
     halfDay,
     halfDayType,
     isStationLeave,
     stationLeaveDetails,
     attachmentUrl,
     chargeableDays: ElmLeaveService.normalizeNumeric(chargeableDays),
     workflowHistory: [{
       timestamp: new Date().toISOString(),
       actor: 'Employee',
       action: 'Draft created',
       detail: 'Leave application created in draft.',
     }],
   });

   return request;
 }

 async submitLeave(payload = {}) {
   const draft = await this.createDraft(payload);
   const balance = await ElmLeaveBalance.findOne({ where: { employeeId: draft.employeeId, categoryId: draft.categoryId } });
   const requestedDays = Number(draft.chargeableDays || 0);

   if (!balance) {
     throw new Error('Insufficient balance.');
   }
   if (Number(balance.balance) < requestedDays) {
     throw new Error('Insufficient balance for this leave request.');
   }

   balance.balance = ElmLeaveService.normalizeNumeric(Number(balance.balance) - requestedDays);
   balance.usedDays = ElmLeaveService.normalizeNumeric(Number(balance.usedDays) + requestedDays);
   await balance.save();

   draft.status = 'Submitted';
   draft.workflowHistory = [
     ...(Array.isArray(draft.workflowHistory) ? draft.workflowHistory : []),
     {
       timestamp: new Date().toISOString(),
       actor: 'Employee',
       action: 'Submitted',
       detail: `Leave submitted for ${requestedDays} day(s).`,
     },
   ];
   await draft.save();

   return draft;
 }

 async getLeaveRequests(filters = {}) {
   const where = {};
   if (filters.employeeId) where.employeeId = Number(filters.employeeId);
   if (filters.categoryId) where.categoryId = Number(filters.categoryId);
   if (filters.status) where.status = filters.status;
   if (filters.fromDate || filters.toDate) {
     where.startDate = {};
     if (filters.fromDate) where.startDate[Op.gte] = filters.fromDate;
     if (filters.toDate) where.startDate[Op.lte] = filters.toDate;
   }
   return ElmLeaveRequest.findAll({ where, order: [['createdAt', 'DESC']] });
 }

 async getPendingApprovals(query = {}) {
   const where = { status: { [Op.in]: ['Submitted', 'Pending Approval', 'Forwarded'] } };
   if (query.employeeId) where.employeeId = Number(query.employeeId);
   return ElmLeaveRequest.findAll({ where, order: [['createdAt', 'ASC']] });
 }

 async getEmployeeBalances(employeeId) {
   if (!employeeId) {
     throw new Error('Employee id is required.');
   }
   return ElmLeaveBalance.findAll({ where: { employeeId: Number(employeeId) } });
 }

 async getLeaveRequest(id) {
   const request = await ElmLeaveRequest.findByPk(id);
   if (!request) {
     throw new Error('Leave request not found.');
   }
   return request;
 }

 async getAuditTrail(id) {
   const request = await this.getLeaveRequest(id);
   return Array.isArray(request.workflowHistory) ? request.workflowHistory : [];
 }

 async cancelLeaveRequest(id, payload = {}) {
   const request = await this.getLeaveRequest(id);
   const allowedStatuses = ['Draft', 'Submitted', 'Pending Approval', 'Forwarded', 'Approved'];
   if (!allowedStatuses.includes(request.status)) {
     throw new Error('This leave request cannot be cancelled in its current state.');
   }

   if (request.status === 'Approved' || request.status === 'Submitted' || request.status === 'Pending Approval' || request.status === 'Forwarded') {
     const balance = await ElmLeaveBalance.findOne({ where: { employeeId: request.employeeId, categoryId: request.categoryId } });
     const adjustment = Number(request.chargeableDays || 0);
     if (balance) {
       balance.balance = ElmLeaveService.normalizeNumeric(Number(balance.balance) + adjustment);
       balance.usedDays = ElmLeaveService.normalizeNumeric(Math.max(0, Number(balance.usedDays) - adjustment));
       await balance.save();
     }
   }

   request.status = 'Cancelled';
   request.decisionRemark = payload.reason || request.decisionRemark || 'Cancelled by employee';
   request.workflowHistory = [
     ...(Array.isArray(request.workflowHistory) ? request.workflowHistory : []),
     { timestamp: new Date().toISOString(), actor: payload.actor || 'Employee', action: 'Cancelled', detail: request.decisionRemark },
   ];
   await request.save();
   return request;
 }

 async withdrawLeaveRequest(id, payload = {}) {
   const request = await this.getLeaveRequest(id);
   if (!['Draft', 'Submitted', 'Pending Approval', 'Forwarded'].includes(request.status)) {
     throw new Error('Only pending requests can be withdrawn.');
   }

   const balance = await ElmLeaveBalance.findOne({ where: { employeeId: request.employeeId, categoryId: request.categoryId } });
   if (balance) {
     balance.balance = ElmLeaveService.normalizeNumeric(Number(balance.balance) + Number(request.chargeableDays || 0));
     balance.usedDays = ElmLeaveService.normalizeNumeric(Math.max(0, Number(balance.usedDays) - Number(request.chargeableDays || 0)));
     await balance.save();
   }

   request.status = 'Cancelled';
   request.decisionRemark = payload.reason || 'Withdrawn by employee';
   request.workflowHistory = [
     ...(Array.isArray(request.workflowHistory) ? request.workflowHistory : []),
     { timestamp: new Date().toISOString(), actor: payload.actor || 'Employee', action: 'Withdrawn', detail: request.decisionRemark },
   ];
   await request.save();
   return request;
 }

 async approveRequest(id, payload = {}) {
   const request = await this.getLeaveRequest(id);
   if (!['Submitted', 'Pending Approval', 'Forwarded'].includes(request.status)) {
     throw new Error('Only pending requests can be approved.');
   }

   const balance = await ElmLeaveBalance.findOne({ where: { employeeId: request.employeeId, categoryId: request.categoryId } });
   if (balance && Number(balance.balance) < Number(request.chargeableDays || 0)) {
     throw new Error('Leave cannot be approved because balance is insufficient.');
   }

   request.status = 'Approved';
   request.decisionRemark = payload.remark || 'Approved';
   request.workflowHistory = [
     ...(Array.isArray(request.workflowHistory) ? request.workflowHistory : []),
     { timestamp: new Date().toISOString(), actor: payload.actor || 'Approver', action: 'Approved', detail: request.decisionRemark },
   ];
   await request.save();
   return request;
 }

 async rejectRequest(id, payload = {}) {
   const request = await this.getLeaveRequest(id);
   if (!['Submitted', 'Pending Approval', 'Forwarded'].includes(request.status)) {
     throw new Error('Only pending requests can be rejected.');
   }
   if (!payload.remark || !String(payload.remark).trim()) {
     throw new Error('Rejection remarks are mandatory.');
   }

   const balance = await ElmLeaveBalance.findOne({ where: { employeeId: request.employeeId, categoryId: request.categoryId } });
   if (balance) {
     balance.balance = ElmLeaveService.normalizeNumeric(Number(balance.balance) + Number(request.chargeableDays || 0));
     balance.usedDays = ElmLeaveService.normalizeNumeric(Math.max(0, Number(balance.usedDays) - Number(request.chargeableDays || 0)));
     await balance.save();
   }

   request.status = 'Rejected';
   request.decisionRemark = payload.remark;
   request.workflowHistory = [
     ...(Array.isArray(request.workflowHistory) ? request.workflowHistory : []),
     { timestamp: new Date().toISOString(), actor: payload.actor || 'Approver', action: 'Rejected', detail: payload.remark },
   ];
   await request.save();
   return request;
 }

 async forwardRequest(id, payload = {}) {
   const request = await this.getLeaveRequest(id);
   if (!['Submitted', 'Pending Approval'].includes(request.status)) {
     throw new Error('Only active requests can be forwarded.');
   }
   request.status = 'Forwarded';
   request.sanctioningAuthority = payload.sanctioningAuthority || request.sanctioningAuthority || 'Higher Authority';
   request.workflowHistory = [
     ...(Array.isArray(request.workflowHistory) ? request.workflowHistory : []),
     { timestamp: new Date().toISOString(), actor: payload.actor || 'Approver', action: 'Forwarded', detail: `Forwarded to ${request.sanctioningAuthority}` },
   ];
   await request.save();
   return request;
 }

 async revokeApprovedLeave(id, payload = {}) {
   const request = await this.getLeaveRequest(id);
   if (request.status !== 'Approved') {
     throw new Error('Only approved leave can be revoked.');
   }

   const balance = await ElmLeaveBalance.findOne({ where: { employeeId: request.employeeId, categoryId: request.categoryId } });
   if (balance) {
     balance.balance = ElmLeaveService.normalizeNumeric(Number(balance.balance) + Number(request.chargeableDays || 0));
     balance.usedDays = ElmLeaveService.normalizeNumeric(Math.max(0, Number(balance.usedDays) - Number(request.chargeableDays || 0)));
     await balance.save();
   }

   request.status = 'Revoked';
   request.decisionRemark = payload.reason || 'Approved leave revoked';
   request.workflowHistory = [
     ...(Array.isArray(request.workflowHistory) ? request.workflowHistory : []),
     { timestamp: new Date().toISOString(), actor: payload.actor || 'Sanctioning Authority', action: 'Revoked', detail: request.decisionRemark },
   ];
   await request.save();
   return request;
 }

 async getCategories() {
   return ElmLeaveCategory.findAll({ order: [['name', 'ASC']] });
 }

 async createCategory(payload = {}) {
   const { name, description, entitlementDays, carryForwardAllowed, carryForwardCap, halfDaySupported, vacationPeriodRequired, medicalEvidenceRequired, minNoticeDays, maxConsecutiveDays } = payload;
   if (!name) {
     throw new Error('Category name is required.');
   }
   return ElmLeaveCategory.create({
     name: String(name).toUpperCase(),
     description,
     entitlementDays: Number(entitlementDays || 0),
     carryForwardAllowed: Boolean(carryForwardAllowed),
     carryForwardCap: carryForwardCap ? Number(carryForwardCap) : null,
     halfDaySupported: Boolean(halfDaySupported),
     vacationPeriodRequired: Boolean(vacationPeriodRequired),
     medicalEvidenceRequired: Boolean(medicalEvidenceRequired),
     minNoticeDays: minNoticeDays ? Number(minNoticeDays) : null,
     maxConsecutiveDays: maxConsecutiveDays ? Number(maxConsecutiveDays) : null,
   });
 }

 async updateCategory(id, payload = {}) {
   const category = await ElmLeaveCategory.findByPk(id);
   if (!category) {
     throw new Error('Category not found.');
   }
   Object.assign(category, payload, {
     entitlementDays: payload.entitlementDays !== undefined ? Number(payload.entitlementDays) : category.entitlementDays,
     carryForwardCap: payload.carryForwardCap !== undefined ? Number(payload.carryForwardCap) : category.carryForwardCap,
   });
   await category.save();
   return category;
 }

 async adjustEmployeeBalance(payload = {}) {
   const { employeeId, categoryId, categoryName, delta } = payload;
   const category = await ElmLeaveService.validateCategory(categoryId, categoryName || null);
   const balance = await ElmLeaveService.ensureBalanceForEmployee(Number(employeeId), category.id);
   const adjustment = ElmLeaveService.normalizeNumeric(Number(delta || 0));
   balance.balance = ElmLeaveService.normalizeNumeric(Number(balance.balance) + adjustment);
   balance.accruedDays = ElmLeaveService.normalizeNumeric(Number(balance.accruedDays) + adjustment);
   await balance.save();
   return balance;
 }

 async getLeaveReports(query = {}) {
   const where = {};
   if (query.employeeId) where.employeeId = Number(query.employeeId);
   if (query.categoryId) where.categoryId = Number(query.categoryId);
   if (query.status) where.status = query.status;

   const rows = await ElmLeaveRequest.findAll({ where, order: [['createdAt', 'DESC']] });
   return rows.map((row) => ({
     id: row.id,
     employeeId: row.employeeId,
     categoryId: row.categoryId,
     startDate: row.startDate,
     endDate: row.endDate,
     status: row.status,
     chargeableDays: row.chargeableDays,
   }));
 }
}

module.exports = ElmLeaveService;
