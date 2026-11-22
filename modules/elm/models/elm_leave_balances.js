const { DataTypes, Model } = require('sequelize');
const { sequelize } = require('../../../db');

class ElmLeaveBalance extends Model {
  static async getForEmployee(employeeId, categoryId) {
   return this.findOne({ where: { employeeId, categoryId } });
  }

  static normalizeValue(value) {
   const numeric = Number(value || 0);
   if (Number.isNaN(numeric)) {
     return 0;
   }
   return Number(numeric.toFixed(2));
  }
}

ElmLeaveBalance.init(
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
   balance: {
     type: DataTypes.DECIMAL(10, 2),
     allowNull: false,
     defaultValue: 0,
     validate: {
       min: 0,
     },
     set(value) {
       this.setDataValue('balance', ElmLeaveBalance.normalizeValue(value));
     },
   },
   accruedDays: {
     type: DataTypes.DECIMAL(10, 2),
     allowNull: false,
     defaultValue: 0,
     set(value) {
       this.setDataValue('accruedDays', ElmLeaveBalance.normalizeValue(value));
     },
   },
   usedDays: {
     type: DataTypes.DECIMAL(10, 2),
     allowNull: false,
     defaultValue: 0,
     set(value) {
       this.setDataValue('usedDays', ElmLeaveBalance.normalizeValue(value));
     },
   },
   carryForwardCap: {
     type: DataTypes.INTEGER,
     allowNull: true,
     defaultValue: null,
   },
   lastAccrualDate: {
     type: DataTypes.DATE,
     allowNull: true,
   },
  },
  {
   sequelize,
   tableName: 'elm_leave_balances',
   timestamps: true,
   indexes: [
     { fields: ['employeeId'] },
     { fields: ['categoryId'] },
     { unique: true, fields: ['employeeId', 'categoryId'] },
   ],
  },
);

ElmLeaveBalance.addHook('beforeValidate', (instance) => {
  const maxBalance = Number(instance.accruedDays || 0) - Number(instance.usedDays || 0);
  if (Number(instance.balance || 0) > maxBalance && maxBalance >= 0) {
   throw new Error('Balance cannot exceed available accrued days');
  }
});

module.exports = ElmLeaveBalance;
