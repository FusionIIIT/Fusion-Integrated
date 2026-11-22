const { DataTypes, Model, Op } = require('sequelize');
const { sequelize } = require('../../../db');

const LEAVE_STATUSES = [
  'Draft',
  'Submitted',
  'Pending Approval',
  'Forwarded',
  'Approved',
  'Rejected',
  'Cancelled',
  'Revoked',
];

class ElmLeaveRequest extends Model {
  static getStatusList() {
   return LEAVE_STATUSES;
  }

  static getStatusEnumValues() {
   return LEAVE_STATUSES.map((status) => status.toLowerCase().replace(/\s+/g, '_'));
  }

  static async findActiveOverlap(employeeId, startDate, endDate, excludeRequestId = null) {
   const rows = await this.findAll({
     where: {
       employeeId,
       status: {
         [Op.in]: ['Submitted', 'Pending Approval', 'Forwarded', 'Approved'],
       },
     },
   });

   return rows.filter((row) => {
     if (row.id === excludeRequestId) {
       return false;
     }

     const rowStart = new Date(row.startDate);
     const rowEnd = new Date(row.endDate);
     const newStart = new Date(startDate);
     const newEnd = new Date(endDate);

     const overlap = newStart <= rowEnd && newEnd >= rowStart;
     if (!overlap) {
       return false;
     }

     const sameDateHalfDay = (
       row.startDate === row.endDate &&
       row.startDate === newStart.toISOString().slice(0, 10) &&
       row.endDate === newEnd.toISOString().slice(0, 10)
     );

     return !(row.halfDay && new Date(row.startDate).toISOString().slice(0, 10) === new Date(startDate).toISOString().slice(0, 10) && sameDateHalfDay);
   });
  }

  static async validateDateRange(employeeId, startDate, endDate, excludeRequestId = null) {
   const start = new Date(startDate);
   const end = new Date(endDate);
   if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
     throw new Error('Leave start and end dates are required.');
   }
   if (end < start) {
     throw new Error('End date cannot be earlier than start date.');
   }

   const overlaps = await this.findActiveOverlap(employeeId, startDate, endDate, excludeRequestId);
   if (overlaps.length) {
     throw new Error('Leave request overlaps with an active or approved leave period.');
   }
  }

  static normalizeStatus(status) {
   const map = {
     draft: 'Draft',
     submitted: 'Submitted',
     'pending approval': 'Pending Approval',
     pending_approval: 'Pending Approval',
     forwarded: 'Forwarded',
     approved: 'Approved',
     rejected: 'Rejected',
     cancelled: 'Cancelled',
     revoked: 'Revoked',
   };
   return map[String(status || '').toLowerCase()] || status;
  }
}

ElmLeaveRequest.init(
  {
   id: {
     type: DataTypes.INTEGER,
     autoIncrement: true,
     primaryKey: true,
   },
   employeeId: {
     type: DataTypes.INTEGER,
     allowNull: false,
     references: {
       model: 'users',
       key: 'id',
     },
     onDelete: 'CASCADE',
   },
   categoryId: {
     type: DataTypes.INTEGER,
     allowNull: false,
     references: {
       model: 'elm_leave_categories',
       key: 'id',
     },
     onDelete: 'CASCADE',
   },
   startDate: {
     type: DataTypes.DATEONLY,
     allowNull: false,
   },
   endDate: {
     type: DataTypes.DATEONLY,
     allowNull: false,
   },
   status: {
     type: DataTypes.ENUM('Draft', 'Submitted', 'Pending Approval', 'Forwarded', 'Approved', 'Rejected', 'Cancelled', 'Revoked'),
     allowNull: false,
     defaultValue: 'Draft',
   },
   halfDay: {
     type: DataTypes.BOOLEAN,
     allowNull: false,
     defaultValue: false,
   },
   halfDayType: {
     type: DataTypes.ENUM('Morning', 'Afternoon', 'None'),
     allowNull: true,
     defaultValue: 'None',
   },
   isStationLeave: {
     type: DataTypes.BOOLEAN,
     allowNull: false,
     defaultValue: false,
   },
   stationLeaveDetails: {
     type: DataTypes.TEXT,
     allowNull: true,
   },
   purpose: {
     type: DataTypes.TEXT,
     allowNull: true,
   },
   reason: {
     type: DataTypes.TEXT,
     allowNull: true,
   },
   attachmentUrl: {
     type: DataTypes.TEXT,
     allowNull: true,
   },
   notes: {
     type: DataTypes.TEXT,
     allowNull: true,
   },
   substituteEmployeeId: {
     type: DataTypes.INTEGER,
     allowNull: true,
     references: {
       model: 'users',
       key: 'id',
     },
   },
   substituteConsentStatus: {
     type: DataTypes.ENUM('Pending', 'Accepted', 'Declined'),
     allowNull: true,
     defaultValue: null,
   },
   unitHeadRecommendation: {
     type: DataTypes.ENUM('Recommended', 'Not Recommended', 'Pending'),
     allowNull: true,
     defaultValue: 'Pending',
   },
   sanctioningAuthority: {
     type: DataTypes.STRING,
     allowNull: true,
   },
   decisionRemark: {
     type: DataTypes.TEXT,
     allowNull: true,
   },
   chargeableDays: {
     type: DataTypes.DECIMAL(10, 2),
     allowNull: false,
     defaultValue: 0,
     set(value) {
       const numeric = Number(value || 0);
       this.setDataValue('chargeableDays', Number.isNaN(numeric) ? 0 : Number(numeric.toFixed(2)));
     },
   },
   workflowHistory: {
     type: DataTypes.JSON,
     allowNull: false,
     defaultValue: [],
   },
  },
  {
   sequelize,
   tableName: 'elm_leave_requests',
   timestamps: true,
   indexes: [
     { fields: ['employeeId'] },
     { fields: ['categoryId'] },
     { fields: ['status'] },
     { fields: ['startDate', 'endDate'] },
   ],
  },
);

ElmLeaveRequest.addHook('beforeValidate', async (instance) => {
  if (instance.status) {
   instance.status = ElmLeaveRequest.normalizeStatus(instance.status);
  }

  if (instance.startDate && instance.endDate) {
   const start = new Date(instance.startDate);
   const end = new Date(instance.endDate);
   if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
     throw new Error('Valid leave dates are required.');
   }
   if (end < start) {
     throw new Error('End date cannot be earlier than start date.');
   }

   if (instance.employeeId) {
     const overlaps = await ElmLeaveRequest.findActiveOverlap(
       instance.employeeId,
       instance.startDate,
       instance.endDate,
       instance.id || null,
     );
     if (overlaps.length && instance.status !== 'Draft') {
       throw new Error('Leave request overlaps with an active or approved leave period.');
     }
   }
  }
});

module.exports = ElmLeaveRequest;
