const { DataTypes, Model } = require('sequelize');
const { sequelize } = require('../../../db');

const DEFAULT_CATEGORY_CONFIG = {
  CL: {
   name: 'CL',
   description: 'Casual Leave',
   entitlementDays: 8,
   carryForwardAllowed: false,
   halfDaySupported: true,
   vacationPeriodRequired: false,
   medicalEvidenceRequired: false,
   minNoticeDays: 0,
   maxConsecutiveDays: 3,
   countWeekendsAndHolidays: false,
  },
  RH: {
   name: 'RH',
   description: 'Restricted Holiday',
   entitlementDays: 2,
   carryForwardAllowed: false,
   halfDaySupported: true,
   vacationPeriodRequired: false,
   medicalEvidenceRequired: false,
   minNoticeDays: 0,
   maxConsecutiveDays: 1,
   countWeekendsAndHolidays: false,
  },
  SCL: {
   name: 'SCL',
   description: 'Special Casual Leave',
   entitlementDays: 15,
   carryForwardAllowed: false,
   halfDaySupported: true,
   vacationPeriodRequired: false,
   medicalEvidenceRequired: false,
   minNoticeDays: 1,
   maxConsecutiveDays: 7,
   countWeekendsAndHolidays: false,
  },
  EL: {
   name: 'EL',
   description: 'Earned Leave',
   entitlementDays: 30,
   carryForwardAllowed: true,
   halfDaySupported: true,
   vacationPeriodRequired: false,
   medicalEvidenceRequired: false,
   minNoticeDays: 1,
   maxConsecutiveDays: 15,
   countWeekendsAndHolidays: true,
   carryForwardCap: 300,
  },
  COL: {
   name: 'COL',
   description: 'Commuted Leave',
   entitlementDays: 20,
   carryForwardAllowed: true,
   halfDaySupported: true,
   vacationPeriodRequired: false,
   medicalEvidenceRequired: true,
   minNoticeDays: 2,
   maxConsecutiveDays: 10,
   countWeekendsAndHolidays: true,
   carryForwardCap: 60,
  },
  VL: {
   name: 'VL',
   description: 'Vacation Leave',
   entitlementDays: 60,
   carryForwardAllowed: false,
   halfDaySupported: true,
   vacationPeriodRequired: true,
   medicalEvidenceRequired: false,
   minNoticeDays: 2,
   maxConsecutiveDays: 30,
   countWeekendsAndHolidays: true,
  },
};

class ElmLeaveCategory extends Model {
  static getDefaultConfig() {
   return DEFAULT_CATEGORY_CONFIG;
  }

  static getCategoryNames() {
   return Object.keys(DEFAULT_CATEGORY_CONFIG);
  }

  static async seedDefaults() {
   const entries = Object.values(DEFAULT_CATEGORY_CONFIG);
   for (const config of entries) {
     const [category] = await this.findOrCreate({
       where: { name: config.name },
       defaults: config,
     });
     if (category) {
       await category.update(config, { fields: Object.keys(config) });
     }
   }
   return this.findAll({ order: [['name', 'ASC']] });
  }
}

ElmLeaveCategory.init(
  {
   id: {
     type: DataTypes.INTEGER,
     autoIncrement: true,
     primaryKey: true,
   },
   name: {
     type: DataTypes.STRING(50),
     allowNull: false,
     unique: true,
     validate: {
       isIn: [['CL', 'RH', 'SCL', 'EL', 'COL', 'VL']],
     },
   },
   description: {
     type: DataTypes.TEXT,
     allowNull: true,
   },
   entitlementDays: {
     type: DataTypes.INTEGER,
     allowNull: false,
     defaultValue: 0,
     validate: {
       min: 0,
       max: 1000,
     },
   },
   carryForwardAllowed: {
     type: DataTypes.BOOLEAN,
     allowNull: false,
     defaultValue: false,
   },
   carryForwardCap: {
     type: DataTypes.INTEGER,
     allowNull: true,
     defaultValue: null,
   },
   halfDaySupported: {
     type: DataTypes.BOOLEAN,
     allowNull: false,
     defaultValue: false,
   },
   vacationPeriodRequired: {
     type: DataTypes.BOOLEAN,
     allowNull: false,
     defaultValue: false,
   },
   medicalEvidenceRequired: {
     type: DataTypes.BOOLEAN,
     allowNull: false,
     defaultValue: false,
   },
   minNoticeDays: {
     type: DataTypes.INTEGER,
     allowNull: true,
     defaultValue: null,
   },
   maxConsecutiveDays: {
     type: DataTypes.INTEGER,
     allowNull: true,
     defaultValue: null,
   },
   countWeekendsAndHolidays: {
     type: DataTypes.BOOLEAN,
     allowNull: false,
     defaultValue: false,
   },
  },
  {
   sequelize,
   tableName: 'elm_leave_categories',
   timestamps: true,
   indexes: [{ fields: ['name'] }],
  },
);

module.exports = ElmLeaveCategory;
