const { DataTypes, Model } = require('sequelize');
const { sequelize } = require('../../../db');

const APPLICATION_STATUSES = [
  'Draft',
  'Submitted',
  'Under Review',
  'Needs Revision',
  'Resubmitted',
  'Approved',
  'Rejected',
  'Expired',
  'Assignment Offered',
  'Attorney Assigned',
  'Pending Review',
  'Budget Approved',
  'Budget Rejected',
  'Escalated',
  'Filed',
  'Granted',
  'Withdrawn',
];

class PmsPatentApplication extends Model {
  static getStatusList() {
    return APPLICATION_STATUSES;
  }

  static normalizeStatus(status) {
    const map = {
      draft: 'Draft',
      submitted: 'Submitted',
      under_review: 'Under Review',
      'under review': 'Under Review',
      needs_revision: 'Needs Revision',
      'needs revision': 'Needs Revision',
      resubmitted: 'Resubmitted',
      approved: 'Approved',
      rejected: 'Rejected',
      expired: 'Expired',
      assignment_offered: 'Assignment Offered',
      'assignment offered': 'Assignment Offered',
      attorney_assigned: 'Attorney Assigned',
      'attorney assigned': 'Attorney Assigned',
      pending_review: 'Pending Review',
      'pending review': 'Pending Review',
      budget_approved: 'Budget Approved',
      'budget approved': 'Budget Approved',
      budget_rejected: 'Budget Rejected',
      'budget rejected': 'Budget Rejected',
      escalated: 'Escalated',
      filed: 'Filed',
      granted: 'Granted',
      withdrawn: 'Withdrawn',
    };
    return map[String(status || '').toLowerCase()] || status;
  }
}

PmsPatentApplication.init(
  {
    id: {
      type: DataTypes.INTEGER,
      autoIncrement: true,
      primaryKey: true,
    },
    applicationCode: {
      type: DataTypes.STRING(64),
      allowNull: true,
      unique: true,
    },
    applicantId: {
      type: DataTypes.INTEGER,
      allowNull: false,
      references: {
        model: 'users',
        key: 'id',
      },
    },
    categoryId: {
      type: DataTypes.INTEGER,
      allowNull: true,
      references: {
        model: 'pms_patent_categories',
        key: 'id',
      },
    },
    title: {
      type: DataTypes.STRING(255),
      allowNull: false,
    },
    abstract: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    detailedDescription: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    claims: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    supportingDocumentUrl: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    supportingDocumentMimeType: {
      type: DataTypes.STRING(120),
      allowNull: true,
    },
    supportingDocumentSizeMb: {
      type: DataTypes.DECIMAL(10, 2),
      allowNull: true,
      defaultValue: null,
    },
    status: {
      type: DataTypes.ENUM(...APPLICATION_STATUSES),
      allowNull: false,
      defaultValue: 'Draft',
    },
    assignedDirectorId: {
      type: DataTypes.INTEGER,
      allowNull: true,
      references: {
        model: 'users',
        key: 'id',
      },
    },
    assignedAttorneyId: {
      type: DataTypes.INTEGER,
      allowNull: true,
      references: {
        model: 'users',
        key: 'id',
      },
    },
    attorneyAssignmentStatus: {
      type: DataTypes.ENUM('Pending', 'Accepted', 'Declined'),
      allowNull: true,
      defaultValue: null,
    },
    preferredAttorneyId: {
      type: DataTypes.INTEGER,
      allowNull: true,
      references: {
        model: 'users',
        key: 'id',
      },
    },
    reviewRemark: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    lastFeedback: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    lastDecisionAt: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    revisionDueDate: {
      type: DataTypes.DATE,
      allowNull: true,
    },
    versionNumber: {
      type: DataTypes.INTEGER,
      allowNull: false,
      defaultValue: 1,
    },
    inventorAgreementCompleted: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: false,
    },
    budgetAmount: {
      type: DataTypes.DECIMAL(12, 2),
      allowNull: false,
      defaultValue: 0,
    },
    budgetStatus: {
      type: DataTypes.ENUM('Pending', 'Approved', 'Rejected', 'Escalated'),
      allowNull: false,
      defaultValue: 'Pending',
    },
    budgetThresholdExceeded: {
      type: DataTypes.BOOLEAN,
      allowNull: false,
      defaultValue: false,
    },
    externalFilingId: {
      type: DataTypes.STRING(120),
      allowNull: true,
    },
    filingDate: {
      type: DataTypes.DATEONLY,
      allowNull: true,
    },
    filingType: {
      type: DataTypes.ENUM('Domestic', 'International'),
      allowNull: true,
    },
    internationalFilingJustification: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    withdrawalReason: {
      type: DataTypes.TEXT,
      allowNull: true,
    },
    statusHistory: {
      type: DataTypes.JSON,
      allowNull: false,
      defaultValue: [],
    },
  },
  {
    sequelize,
    tableName: 'pms_patent_applications',
    timestamps: true,
    indexes: [
      { fields: ['applicationCode'] },
      { fields: ['applicantId'] },
      { fields: ['categoryId'] },
      { fields: ['status'] },
      { fields: ['assignedDirectorId'] },
      { fields: ['assignedAttorneyId'] },
    ],
  },
);

PmsPatentApplication.addHook('beforeValidate', (instance) => {
  if (instance.status) {
    instance.status = PmsPatentApplication.normalizeStatus(instance.status);
  }
});

PmsPatentApplication.addHook('beforeCreate', (instance) => {
  if (!instance.applicationCode) {
    instance.applicationCode = `PMS-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
  }
});

module.exports = PmsPatentApplication;
