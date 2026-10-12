// path/to/modules/elm/models/elm_leave_requests.js
import { DataTypes, Model } from 'sequelize';

class ElmLeaveRequest extends Model {}

ElmLeaveRequest.init({
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
    type: DataTypes.DATE,
    allowNull: false,
  },
  endDate: {
    type: DataTypes.DATE,
    allowNull: false,
  },
  status: {
    type: DataTypes.STRING,
    allowNull: false,
    defaultValue: 'draft',
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
  tableName: 'elm_leave_requests',
});

export default ElmLeaveRequest;
