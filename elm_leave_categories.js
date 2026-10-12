// path/to/modules/elm/models/elm_leave_categories.js
import { DataTypes, Model } from 'sequelize';

class ElmLeaveCategory extends Model {}

ElmLeaveCategory.init({
  name: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
  },
  description: {
    type: DataTypes.TEXT,
    allowNull: true,
  },
}, {
  sequelize: null, // This will be set by the Sequelize instance
  tableName: 'elm_leave_categories',
});

export default ElmLeaveCategory;
