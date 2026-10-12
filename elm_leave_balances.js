// path/to/modules/elm/models/elm_leave_balances.js
import { DataTypes, Model } from 'sequelize';

class ElmLeaveBalance extends Model {}

ElmLeaveBalance.init({
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
    type: DataTypes.INTEGER,
    allowNull: false,
    defaultValue: 0,
  },
  createdAt: {
    type: DataTypes.DATE,
    allowNull: false,
    defaultValue: DataTypes.NOW,
  },
  updatedAt: {
    type: DataTypes.DATE,
    allowNull: false,
    defaultValue: DataTypes.NOW,
  },
}, {
  sequelize: null, // This will be set by the Sequelize instance
  tableName: 'elm_leave_balances',
});

export default ElmLeaveBalance;
