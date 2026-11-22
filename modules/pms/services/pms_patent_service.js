const { Op } = require('sequelize');
const {
  PmsPatentApplication,
  PmsPatentCategory,
  PmsPatentInventor,
  PmsPatentReview,
} = require('../models');

class PmsPatentService {
  static addDays(dateValue, days) {
    const date = new Date(dateValue);
    date.setDate(date.getDate() + days);
    return date;
  }

  static toDateString(dateValue) {
    const date = new Date(dateValue);
    return date.toISOString().slice(0, 10);
  }

  static ensureStatusTransition(currentStatus, nextStatus) {
    const allowed = {
      Draft: ['Submitted', 'Withdrawn'],
      Submitted: ['Under Review', 'Withdrawn'],
      'Under Review': ['Approved', 'Rejected', 'Needs Revision'],
      'Needs Revision': ['Resubmitted', 'Expired', 'Withdrawn'],
      Rejected: ['Resubmitted', 'Withdrawn', 'Expired'],
      Resubmitted: ['Under Review', 'Withdrawn'],
      Approved: ['Assignment Offered', 'Budget Approved', 'Budget Rejected', 'Escalated', 'Withdrawn'],
      'Assignment Offered': ['Attorney Assigned', 'Pending Review'],
      'Pending Review': ['Assignment Offered'],
      'Attorney Assigned': ['Budget Approved', 'Budget Rejected', 'Escalated', 'Filed'],
      'Budget Approved': ['Filed'],
      'Budget Rejected': [],
      Escalated: [],
      Filed: ['Granted'],
      Granted: [],
      Expired: [],
      Withdrawn: [],
    };
    if (!(allowed[currentStatus] || []).includes(nextStatus)) {
      throw new Error(`Invalid status transition: ${currentStatus} -> ${nextStatus}`);
    }
  }

  static pushHistory(application, actor, action, detail, nextStatus = application.status) {
    const history = Array.isArray(application.statusHistory) ? application.statusHistory : [];
    return [
      ...history,
      {
        timestamp: new Date().toISOString(),
        actor: actor || 'System',
        action,
        detail: detail || '',
        status: nextStatus,
      },
    ];
  }

  async ensureCategoryExists(categoryId) {
    if (!categoryId) {
      return null;
    }
    const category = await PmsPatentCategory.findByPk(Number(categoryId));
    if (!category || !category.isActive) {
      throw new Error('Invalid patent category.');
    }
    return category;
  }

  async ensureApplication(id) {
    const application = await PmsPatentApplication.findByPk(Number(id));
    if (!application) {
      throw new Error('Patent application not found.');
    }
    return application;
  }

  async setInventors(applicationId, inventors = []) {
    if (!Array.isArray(inventors) || !inventors.length) {
      return [];
    }

    let totalShare = 0;
    const rows = [];
    for (const inventor of inventors) {
      if (!inventor || !inventor.inventorName) {
        throw new Error('Inventor name is required.');
      }
      const share = Number(inventor.ownershipShare || 0);
      if (Number.isNaN(share) || share < 0 || share > 100) {
        throw new Error('Inventor ownership share must be between 0 and 100.');
      }
      totalShare += share;
      rows.push({
        applicationId,
        inventorId: inventor.inventorId ? Number(inventor.inventorId) : null,
        inventorName: inventor.inventorName,
        inventorEmail: inventor.inventorEmail || null,
        ownershipShare: share,
        consentProvided: Boolean(inventor.consentProvided),
        agreementSigned: Boolean(inventor.agreementSigned),
      });
    }

    if (totalShare > 100.0001) {
      throw new Error('Total inventor ownership share cannot exceed 100.');
    }

    await PmsPatentInventor.destroy({ where: { applicationId } });
    return PmsPatentInventor.bulkCreate(rows);
  }

  validateSubmissionData(payload = {}) {
    if (!payload.title || !String(payload.title).trim()) {
      throw new Error('Patent title is required.');
    }
    if (!payload.abstract || !String(payload.abstract).trim()) {
      throw new Error('Patent abstract is required.');
    }
    if (!payload.detailedDescription || !String(payload.detailedDescription).trim()) {
      throw new Error('Detailed description is required.');
    }
    if (!payload.claims || !String(payload.claims).trim()) {
      throw new Error('Patent claims are required.');
    }
    if (payload.supportingDocumentMimeType && String(payload.supportingDocumentMimeType).toLowerCase() !== 'application/pdf') {
      throw new Error('Only PDF supporting documents are allowed.');
    }
    if (payload.supportingDocumentSizeMb !== undefined && Number(payload.supportingDocumentSizeMb) > 50) {
      throw new Error('Supporting document size cannot exceed 50 MB.');
    }
  }

  async createDraft(payload = {}) {
    if (!payload.applicantId || !Number.isFinite(Number(payload.applicantId))) {
      throw new Error('Applicant id is required.');
    }
    if (!payload.title || !String(payload.title).trim()) {
      throw new Error('Patent title is required for draft.');
    }
    await this.ensureCategoryExists(payload.categoryId);

    const application = await PmsPatentApplication.create({
      applicantId: Number(payload.applicantId),
      categoryId: payload.categoryId ? Number(payload.categoryId) : null,
      title: payload.title,
      abstract: payload.abstract || '',
      detailedDescription: payload.detailedDescription || '',
      claims: payload.claims || '',
      supportingDocumentUrl: payload.supportingDocumentUrl || null,
      supportingDocumentMimeType: payload.supportingDocumentMimeType || null,
      supportingDocumentSizeMb: payload.supportingDocumentSizeMb ? Number(payload.supportingDocumentSizeMb) : null,
      status: 'Draft',
      preferredAttorneyId: payload.preferredAttorneyId ? Number(payload.preferredAttorneyId) : null,
      inventorAgreementCompleted: Boolean(payload.inventorAgreementCompleted),
      budgetAmount: payload.budgetAmount ? Number(payload.budgetAmount) : 0,
      statusHistory: [{
        timestamp: new Date().toISOString(),
        actor: payload.actor || 'Applicant',
        action: 'Draft Created',
        detail: 'Patent application draft created.',
        status: 'Draft',
      }],
    });

    if (Array.isArray(payload.inventors) && payload.inventors.length) {
      await this.setInventors(application.id, payload.inventors);
    }

    return this.getApplication(application.id);
  }

  async submitApplication(payload = {}) {
    let application;
    if (payload.applicationId) {
      application = await this.ensureApplication(payload.applicationId);
      if (application.status !== 'Draft') {
        throw new Error('Only draft applications can be submitted.');
      }
    } else {
      application = await this.createDraft(payload);
      application = await this.ensureApplication(application.id);
    }

    const updateData = {
      title: payload.title !== undefined ? payload.title : application.title,
      abstract: payload.abstract !== undefined ? payload.abstract : application.abstract,
      detailedDescription: payload.detailedDescription !== undefined ? payload.detailedDescription : application.detailedDescription,
      claims: payload.claims !== undefined ? payload.claims : application.claims,
      supportingDocumentUrl: payload.supportingDocumentUrl !== undefined ? payload.supportingDocumentUrl : application.supportingDocumentUrl,
      supportingDocumentMimeType: payload.supportingDocumentMimeType !== undefined ? payload.supportingDocumentMimeType : application.supportingDocumentMimeType,
      supportingDocumentSizeMb: payload.supportingDocumentSizeMb !== undefined ? Number(payload.supportingDocumentSizeMb || 0) : application.supportingDocumentSizeMb,
    };
    this.validateSubmissionData(updateData);

    if (payload.categoryId !== undefined) {
      await this.ensureCategoryExists(payload.categoryId);
      application.categoryId = payload.categoryId ? Number(payload.categoryId) : null;
    }
    Object.assign(application, updateData);
    application.inventorAgreementCompleted = payload.inventorAgreementCompleted !== undefined
      ? Boolean(payload.inventorAgreementCompleted)
      : application.inventorAgreementCompleted;

    if (Array.isArray(payload.inventors)) {
      await this.setInventors(application.id, payload.inventors);
    }

    PmsPatentService.ensureStatusTransition(application.status, 'Submitted');
    application.status = 'Submitted';
    application.lastDecisionAt = new Date();
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'Applicant',
      'Submitted',
      'Patent application submitted.',
      'Submitted',
    );
    await application.save();

    return this.getApplication(application.id);
  }

  async getApplications(filters = {}) {
    await this.expireOverdueApplications();

    const where = {};
    if (filters.applicantId) where.applicantId = Number(filters.applicantId);
    if (filters.categoryId) where.categoryId = Number(filters.categoryId);
    if (filters.status) where.status = PmsPatentApplication.normalizeStatus(filters.status);
    if (filters.assignedDirectorId) where.assignedDirectorId = Number(filters.assignedDirectorId);
    if (filters.assignedAttorneyId) where.assignedAttorneyId = Number(filters.assignedAttorneyId);
    if (filters.search) {
      where[Op.or] = [
        { title: { [Op.like]: `%${filters.search}%` } },
        { applicationCode: { [Op.like]: `%${filters.search}%` } },
      ];
    }

    return PmsPatentApplication.findAll({
      where,
      include: [{ model: PmsPatentCategory, as: 'category' }, { model: PmsPatentInventor, as: 'inventors' }],
      order: [['createdAt', 'DESC']],
    });
  }

  async getApplication(id) {
    await this.expireOverdueApplications();

    const application = await PmsPatentApplication.findByPk(Number(id), {
      include: [
        { model: PmsPatentCategory, as: 'category' },
        { model: PmsPatentInventor, as: 'inventors' },
        { model: PmsPatentReview, as: 'reviews' },
      ],
      order: [[{ model: PmsPatentReview, as: 'reviews' }, 'createdAt', 'DESC']],
    });
    if (!application) {
      throw new Error('Patent application not found.');
    }
    return application;
  }

  async assignDirector(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (!['Submitted', 'Resubmitted'].includes(application.status)) {
      throw new Error('Only submitted or resubmitted applications can be assigned to a director.');
    }
    if (!payload.directorId || !Number.isFinite(Number(payload.directorId))) {
      throw new Error('Director id is required.');
    }

    const directorId = Number(payload.directorId);
    if (directorId === application.applicantId) {
      throw new Error('Director cannot review own application.');
    }
    const conflictingInventor = await PmsPatentInventor.findOne({
      where: { applicationId: application.id, inventorId: directorId },
    });
    if (conflictingInventor) {
      throw new Error('Director cannot review an application where they are listed as inventor.');
    }

    PmsPatentService.ensureStatusTransition(application.status, 'Under Review');
    application.assignedDirectorId = directorId;
    application.status = 'Under Review';
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'PCC_ADMIN',
      'Director Assigned',
      `Assigned to director ${directorId}.`,
      'Under Review',
    );
    await application.save();

    return this.getApplication(application.id);
  }

  async reviewApplication(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (application.status !== 'Under Review') {
      throw new Error('Application must be under review.');
    }
    if (!payload.decision) {
      throw new Error('Decision is required.');
    }
    if (!payload.justification || String(payload.justification).trim().length < 50) {
      throw new Error('Review justification must be at least 50 characters.');
    }

    const decisionMap = {
      approve: 'Approved',
      approved: 'Approved',
      reject: 'Rejected',
      rejected: 'Rejected',
      needs_revision: 'Needs Revision',
      'needs revision': 'Needs Revision',
      revision: 'Needs Revision',
    };
    const decisionStatus = decisionMap[String(payload.decision).toLowerCase()];
    if (!decisionStatus) {
      throw new Error('Decision must be Approve, Reject, or Needs Revision.');
    }

    PmsPatentService.ensureStatusTransition(application.status, decisionStatus);
    application.status = decisionStatus;
    application.reviewRemark = payload.justification;
    application.lastFeedback = payload.justification;
    application.lastDecisionAt = new Date();
    if (decisionStatus === 'Needs Revision' || decisionStatus === 'Rejected') {
      application.revisionDueDate = PmsPatentService.addDays(new Date(), 60);
    } else {
      application.revisionDueDate = null;
    }
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'Director',
      'Review Decision',
      `${decisionStatus}: ${payload.justification}`,
      decisionStatus,
    );
    await application.save();

    await PmsPatentReview.create({
      applicationId: application.id,
      reviewerId: payload.reviewerId ? Number(payload.reviewerId) : Number(application.assignedDirectorId || 0),
      reviewerRole: payload.reviewerRole || 'Director',
      decision: decisionStatus === 'Approved' ? 'Approve' : decisionStatus === 'Rejected' ? 'Reject' : 'Needs Revision',
      justification: payload.justification,
      reviewVersion: application.versionNumber,
    });

    return this.getApplication(application.id);
  }

  async resubmitApplication(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (!['Needs Revision', 'Rejected'].includes(application.status)) {
      throw new Error('Only needs revision or rejected applications can be resubmitted.');
    }
    if (!payload.revisionNote || String(payload.revisionNote).trim().length < 10) {
      throw new Error('Revision note is required and must address review feedback.');
    }
    if (application.revisionDueDate && new Date(application.revisionDueDate) < new Date()) {
      application.status = 'Expired';
      application.statusHistory = PmsPatentService.pushHistory(
        application,
        payload.actor || 'System',
        'Expired',
        'Resubmission period expired after 60 days.',
        'Expired',
      );
      await application.save();
      throw new Error('Resubmission deadline has expired.');
    }

    PmsPatentService.ensureStatusTransition(application.status, 'Resubmitted');
    application.versionNumber = Number(application.versionNumber || 1) + 1;
    application.status = 'Resubmitted';
    application.lastFeedback = payload.revisionNote;
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'Applicant',
      'Resubmitted',
      payload.revisionNote,
      'Resubmitted',
    );
    await application.save();

    return this.getApplication(application.id);
  }

  async assignAttorney(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (!['Approved', 'Pending Review'].includes(application.status)) {
      throw new Error('Only approved or pending review applications can be assigned to an attorney.');
    }
    if (!payload.attorneyId || !Number.isFinite(Number(payload.attorneyId))) {
      throw new Error('Attorney id is required.');
    }
    if (payload.isOnApprovedPanel === false && payload.exceptionApproved !== true) {
      throw new Error('Attorney must be in approved panel unless an exception is recorded.');
    }

    PmsPatentService.ensureStatusTransition(application.status, 'Assignment Offered');
    application.assignedAttorneyId = Number(payload.attorneyId);
    application.attorneyAssignmentStatus = 'Pending';
    application.status = 'Assignment Offered';
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'PCC_ADMIN',
      'Attorney Assigned',
      `Assignment offered to attorney ${payload.attorneyId}.`,
      'Assignment Offered',
    );
    await application.save();

    return this.getApplication(application.id);
  }

  async respondAttorneyAssignment(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (application.status !== 'Assignment Offered') {
      throw new Error('Attorney response is allowed only for assignment offered applications.');
    }
    const response = String(payload.response || '').toLowerCase();
    if (!['accept', 'decline'].includes(response)) {
      throw new Error('Response must be accept or decline.');
    }

    const nextStatus = response === 'accept' ? 'Attorney Assigned' : 'Pending Review';
    PmsPatentService.ensureStatusTransition(application.status, nextStatus);
    application.attorneyAssignmentStatus = response === 'accept' ? 'Accepted' : 'Declined';
    application.status = nextStatus;
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'Attorney',
      'Attorney Assignment Response',
      response === 'accept' ? 'Attorney accepted assignment.' : 'Attorney declined assignment.',
      nextStatus,
    );
    await application.save();

    return this.getApplication(application.id);
  }

  async reviewBudget(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (!['Approved', 'Attorney Assigned'].includes(application.status)) {
      throw new Error('Budget review requires approved or attorney assigned status.');
    }
    if (payload.budgetAmount === undefined || Number.isNaN(Number(payload.budgetAmount))) {
      throw new Error('Budget amount is required.');
    }
    if (!payload.decision) {
      throw new Error('Budget decision is required.');
    }

    const threshold = payload.threshold !== undefined ? Number(payload.threshold) : 100000;
    const amount = Number(payload.budgetAmount);
    const decision = String(payload.decision).toLowerCase();
    let nextStatus;
    let budgetStatus;

    if (decision === 'approve' && amount <= threshold) {
      nextStatus = 'Budget Approved';
      budgetStatus = 'Approved';
    } else if (decision === 'reject') {
      nextStatus = 'Budget Rejected';
      budgetStatus = 'Rejected';
    } else {
      nextStatus = 'Escalated';
      budgetStatus = 'Escalated';
    }

    PmsPatentService.ensureStatusTransition(application.status, nextStatus);
    application.budgetAmount = amount;
    application.budgetStatus = budgetStatus;
    application.budgetThresholdExceeded = amount > threshold;
    application.status = nextStatus;
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'Director',
      'Budget Review',
      `Budget ${budgetStatus.toLowerCase()} for amount ${amount}.`,
      nextStatus,
    );
    await application.save();

    return this.getApplication(application.id);
  }

  async recordFiling(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (!['Attorney Assigned', 'Budget Approved'].includes(application.status)) {
      throw new Error('Only attorney assigned or budget approved applications can be filed.');
    }
    if (!application.inventorAgreementCompleted) {
      throw new Error('Inventor agreements must be completed before filing.');
    }
    if (!payload.externalFilingId || !String(payload.externalFilingId).trim()) {
      throw new Error('External filing id is required.');
    }
    if (!payload.filingDate) {
      throw new Error('Filing date is required.');
    }
    const filingType = payload.filingType || 'Domestic';
    if (filingType === 'International' && !payload.internationalFilingJustification) {
      throw new Error('International filing requires additional justification.');
    }

    PmsPatentService.ensureStatusTransition(application.status, 'Filed');
    application.externalFilingId = payload.externalFilingId;
    application.filingDate = PmsPatentService.toDateString(payload.filingDate);
    application.filingType = filingType;
    application.internationalFilingJustification = payload.internationalFilingJustification || null;
    application.status = 'Filed';
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'Attorney',
      'Filed',
      `Filed externally with id ${payload.externalFilingId}.`,
      'Filed',
    );
    await application.save();

    return this.getApplication(application.id);
  }

  async markGranted(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (application.status !== 'Filed') {
      throw new Error('Only filed applications can be marked granted.');
    }

    PmsPatentService.ensureStatusTransition(application.status, 'Granted');
    application.status = 'Granted';
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'PCC_ADMIN',
      'Granted',
      payload.remark || 'Patent grant recorded.',
      'Granted',
    );
    await application.save();
    return this.getApplication(application.id);
  }

  async withdrawApplication(id, payload = {}) {
    const application = await this.ensureApplication(id);
    if (['Filed', 'Granted', 'Withdrawn', 'Expired'].includes(application.status)) {
      throw new Error('Application cannot be withdrawn at current status.');
    }

    PmsPatentService.ensureStatusTransition(application.status, 'Withdrawn');
    application.status = 'Withdrawn';
    application.withdrawalReason = payload.reason || 'Withdrawn by applicant';
    application.statusHistory = PmsPatentService.pushHistory(
      application,
      payload.actor || 'Applicant',
      'Withdrawn',
      application.withdrawalReason,
      'Withdrawn',
    );
    await application.save();
    return this.getApplication(application.id);
  }

  async expireOverdueApplications() {
    const rows = await PmsPatentApplication.findAll({
      where: {
        status: { [Op.in]: ['Needs Revision', 'Rejected'] },
        revisionDueDate: { [Op.lt]: new Date() },
      },
    });

    for (const application of rows) {
      if (application.status === 'Expired') {
        continue;
      }
      application.status = 'Expired';
      application.statusHistory = PmsPatentService.pushHistory(
        application,
        'System',
        'Expired',
        'Resubmission period expired after 60 days.',
        'Expired',
      );
      await application.save();
    }
  }

  async getCategories() {
    return PmsPatentCategory.findAll({ order: [['name', 'ASC']] });
  }

  async createCategory(payload = {}) {
    if (!payload.name || !String(payload.name).trim()) {
      throw new Error('Category name is required.');
    }
    return PmsPatentCategory.create({
      name: payload.name,
      description: payload.description || null,
      isActive: payload.isActive !== undefined ? Boolean(payload.isActive) : true,
    });
  }

  async updateCategory(id, payload = {}) {
    const category = await PmsPatentCategory.findByPk(Number(id));
    if (!category) {
      throw new Error('Category not found.');
    }

    if (payload.name !== undefined && !String(payload.name).trim()) {
      throw new Error('Category name cannot be empty.');
    }

    Object.assign(category, {
      name: payload.name !== undefined ? payload.name : category.name,
      description: payload.description !== undefined ? payload.description : category.description,
      isActive: payload.isActive !== undefined ? Boolean(payload.isActive) : category.isActive,
    });
    await category.save();
    return category;
  }
}

module.exports = PmsPatentService;
